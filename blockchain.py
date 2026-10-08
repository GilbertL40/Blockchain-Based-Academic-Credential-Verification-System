"""A local, hash-chained block ledger for certificate records.

Each issued certificate gets one block. A block's hash is derived from its own
fields plus the previous block's hash, so altering any block breaks the chain
from that point forward. Each block also stores a hash of the certificate's
core data at issuance time, so editing that certificate afterward can be
detected even though the certificates table itself isn't chained.
"""

import hashlib
from datetime import datetime, timezone

from models import db

GENESIS_PREVIOUS_HASH = '0' * 64


class Block(db.Model):
    __tablename__ = 'blocks'

    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer, unique=True, nullable=False)
    cert_id = db.Column(db.String(20), nullable=True)  # loose reference, null for genesis
    record_hash = db.Column(db.String(64), nullable=True)
    previous_hash = db.Column(db.String(64), nullable=False)
    block_hash = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.String(40), nullable=False)


def compute_record_hash(cert):
    raw = f"{cert.id}|{cert.student_id}|{cert.course}|{cert.issued_date}|{cert.file_hash or ''}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def compute_block_hash(index, timestamp, previous_hash, cert_id, record_hash):
    raw = f"{index}|{timestamp}|{previous_hash}|{cert_id or ''}|{record_hash or ''}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _ensure_genesis():
    genesis = Block.query.filter_by(index=0).first()
    if genesis:
        return genesis
    timestamp = datetime.now(timezone.utc).isoformat()
    block_hash = compute_block_hash(0, timestamp, GENESIS_PREVIOUS_HASH, None, None)
    genesis = Block(
        index=0, cert_id=None, record_hash=None,
        previous_hash=GENESIS_PREVIOUS_HASH, block_hash=block_hash, timestamp=timestamp,
    )
    db.session.add(genesis)
    db.session.commit()
    return genesis


def add_certificate_block(cert, timestamp=None):
    """Appends a new block anchoring this certificate's current data. Returns the new Block."""
    last_block = Block.query.order_by(Block.index.desc()).first() or _ensure_genesis()
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    record_hash = compute_record_hash(cert)
    new_index = last_block.index + 1
    block_hash = compute_block_hash(new_index, timestamp, last_block.block_hash, cert.id, record_hash)

    block = Block(
        index=new_index, cert_id=cert.id, record_hash=record_hash,
        previous_hash=last_block.block_hash, block_hash=block_hash, timestamp=timestamp,
    )
    db.session.add(block)
    db.session.commit()
    return block


def verify_certificate(cert):
    """Recomputes the certificate's hash against the block recorded at issuance time."""
    block = Block.query.filter_by(cert_id=cert.id).first()
    if not block:
        return False, "No blockchain record found for this certificate."
    current_hash = compute_record_hash(cert)
    if current_hash != block.record_hash:
        return False, "This certificate's data no longer matches its blockchain record — possible tampering."
    return True, None


def verify_chain():
    """Walks the whole chain, checking block links and each certificate's record hash. Returns a list of problems (empty = intact)."""
    blocks = Block.query.order_by(Block.index.asc()).all()
    problems = []
    previous_hash = GENESIS_PREVIOUS_HASH

    for block in blocks:
        expected_hash = compute_block_hash(block.index, block.timestamp, previous_hash, block.cert_id, block.record_hash)
        if block.previous_hash != previous_hash:
            problems.append(f"Block {block.index}: previous_hash does not match block {block.index - 1}'s hash.")
        elif block.block_hash != expected_hash:
            problems.append(f"Block {block.index}: stored block_hash does not match its recomputed hash (block tampered).")

        if block.cert_id:
            from models import Certificate
            cert = Certificate.query.get(block.cert_id)
            if not cert:
                problems.append(f"Block {block.index}: certificate {block.cert_id} no longer exists.")
            elif compute_record_hash(cert) != block.record_hash:
                problems.append(f"Block {block.index}: certificate {block.cert_id}'s data no longer matches its recorded hash (certificate tampered).")

        previous_hash = block.block_hash

    return problems
