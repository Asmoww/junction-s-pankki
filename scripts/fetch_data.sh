#!/usr/bin/env bash
# Download the S-Pankki challenge dataset into data/raw/ (gitignored, challenge-only data).
# The transactions CSV is in Git LFS; fetch it directly and verify the hash.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw
BASE=https://raw.githubusercontent.com/hackjunction/Junction-2026-S-pankki/main
LFS=https://media.githubusercontent.com/media/hackjunction/Junction-2026-S-pankki/main
for f in tx_customers_junction.csv mtg_negotiation_history.csv mtg_tx_customer_link_and_final_mtg_infio.csv README.md; do
  curl -fsSL -o "data/raw/$f" "$BASE/$f"
done
curl -fsSL -o data/raw/tx.part "$LFS/tx_junction_transactions.csv"
echo "49b3265d8e44e751de305a074dcffcda732bb79aa1e07b46fcca774ce76f1e63  data/raw/tx.part" | sha256sum -c -
mv data/raw/tx.part data/raw/tx_junction_transactions.csv
ls -l data/raw
