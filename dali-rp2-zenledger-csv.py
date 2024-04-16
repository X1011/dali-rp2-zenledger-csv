# Copyright 2024 Daniel Smith
#
import csv
from datetime import datetime
import argparse

# Input and output file paths
parser = argparse.ArgumentParser()
parser.add_argument("zenledger_filename", help="Zenledger csv file", type=str)
args = parser.parse_args()

in_filename    = "zenledger_manual_in.csv"
out_filename   = "zenledger_manual_out.csv"

# Mapping ZenLedger transaction types to DaLI transaction types
type_map = {
    "Receive": "Receive",
    "Send": "Send",
    "buy": "Buy",
    "sell": "Sell",
    "trade": "trade",
    "fee": "Fee",
    "staking_reward": "Staking",
    "dividend_received": "Interest",
}

def format_timestamp(timestamp_str):
    # Handle the 'Z' at the end of the timestamp
    if timestamp_str.endswith("Z"):
        timestamp_value = datetime.fromisoformat(timestamp_str[:-1] + "+00:00")
    else:
        timestamp_value = datetime.fromisoformat(timestamp_str)
    return timestamp_value.strftime("%Y-%m-%d %H:%M:%S%z")

def calculate_spot_price(in_currency, in_amount, out_currency, out_amount):
    if in_currency == "USD":
        return str(float(in_amount) / float(out_amount))
    elif out_currency == "USD":
        return str(float(out_amount) / float(in_amount))
    else:
        return "__unknown"

def make_common_fields(row, id_suffix=''):
    return {
        "Unique ID": row["Txid"] + id_suffix,
        "Timestamp": format_timestamp(row["Timestamp"]),
        "Exchange": row["Exchange(optional)"],
        "Holder": "unknown",  # not provided in the input
        "Spot Price": calculate_spot_price(row["IN Currency"], row["IN Amount"], row["Out Currency"], row["Out Amount"]),
    }

def make_fee_transaction(row):
    currency = row["Fee Currency"]
    amount = row["Fee Amount"]
    return {
        "Transaction Type": "Fee",
        **make_common_fields(row, "-fee"),
        "Asset": currency,
        "Spot Price": "__unknown",
        "USD Fee":    amount if currency == "USD" else None,
        "Crypto Fee": amount if currency != "USD" else "0", # DaLI requires explicit Crypto Fee for outgoing transactions
        "Crypto Out No Fee": "0",
        "Notes": "generated Fee transaction"
    }

def calculate_fee(row, asset_currency, outgoing: bool):
    amount = row["Fee Amount"]
    if (amount is None) or (float(amount) <= 0):
        return {"Crypto Fee": "0"}, []
    
    elif row["Fee Currency"] == "USD":
        # DaLI requires an explicit Crypto Fee entry for outgoing transactions, but does not accept both Crypto and USD fee entries for incoming, so we need to special case it
        if outgoing:
            return {"USD Fee": amount, "Crypto Fee": "0"}, []
        else:
            return {"USD Fee": amount}, []
    
    elif row["Fee Currency"] == asset_currency:
        return {"Crypto Fee": amount}, []
    else:
        return {"Crypto Fee": "0"}, [make_fee_transaction(row)]

def convert_incoming(row, transaction_type):
    asset_currency = row["IN Currency"]
    fee_entry, fee_txs = calculate_fee(row, asset_currency, outgoing=False)
    
    return [{
        # override the receive transaction type to one DaLI will recognize. If it is part of a transfer, it should match up with the outgoing side later by id. Otherwise, it may be a random airdrop.
        "Transaction Type": transaction_type if transaction_type != "Receive" else "Airdrop",
        **make_common_fields(row),
        "Asset": asset_currency,
        "Crypto In": row["IN Amount"],
        "USD In No Fee": row["Out Amount"],
        **fee_entry
    }], fee_txs

def convert_outgoing(row, transaction_type):
    asset_currency = row["Out Currency"]
    fee_entry, fee_txs = calculate_fee(row, asset_currency, outgoing=True)

    return [], [{
        # override the send transaction type to one DaLI will recognize, then it should match up with the incoming side later by id. If it got lost, however, consider it a gift.
        "Transaction Type": transaction_type if transaction_type != "Send" else "Gift",
        **make_common_fields(row),
        "Asset": asset_currency,
        "Crypto Out No Fee": row["Out Amount"],
        "USD Out No Fee": row["IN Amount"],
        **fee_entry
    }, *fee_txs]

def convert_trade(row):
    fee_entry, fee_txs = calculate_fee(row, row["Out Currency"], outgoing=True)    
    out_tx = {
        "Transaction Type": "Sell",
        **make_common_fields(row, "-sell"),
        "Asset": row["Out Currency"],
        "Crypto Out No Fee": row["Out Amount"],
        "Notes": "generated Sell-side of trade",
        **fee_entry
    }
    in_tx = {
        "Transaction Type": "Buy",
        **make_common_fields(row, "-buy"),
        "Asset": row["IN Currency"],
        "Crypto In": row["IN Amount"],
        "Notes": "generated Buy-side of trade"
    }
    return [in_tx], [out_tx, *fee_txs]

def convert_row(row, in_writer, out_writer):
    transaction_type = type_map.get(row["Type"], "Unknown")

    if transaction_type in ["Receive", "Buy", "Interest", "Staking"]:
        in_txs, out_txs = convert_incoming(row, transaction_type)
    elif transaction_type in ["Send", "Sell", "Fee"]:
        in_txs, out_txs = convert_outgoing(row, transaction_type)
    elif transaction_type == "trade":
        in_txs, out_txs = convert_trade(row)
    else:
        print(f"Skipping unknown transaction type: {row['Type']}")
        return
    
    for tx in in_txs:  in_writer.writerow(tx)
    for tx in out_txs: out_writer.writerow(tx)
    
def convert_csv():
    with open(args.zenledger_filename, "r", encoding="utf-8") as zenledger_file, \
         open(in_filename, "w", encoding="utf-8") as in_file, \
         open(out_filename, "w", encoding="utf-8") as out_file:

        # ZenLedger csv fields for reading: Timestamp, Type, IN Amount, IN Currency, Out Amount, Out Currency, Fee Amount, Fee Currency, Exchange(optional), US Based, Txid
        zenledger_reader = csv.DictReader(zenledger_file)
        in_writer = csv.DictWriter(in_file, fieldnames=["Unique ID", "Timestamp", "Asset", "Exchange", "Holder", "Transaction Type", "Spot Price", "Crypto In", "Crypto Fee", "USD In No Fee", "USD In With Fee", "USD Fee", "fiat_ticker", "Notes"])
        out_writer = csv.DictWriter(out_file, fieldnames=["Unique ID", "Timestamp", "Asset", "Exchange", "Holder", "Transaction Type", "Spot Price", "Crypto Out No Fee", "Crypto Fee", "Crypto Out With Fee", "USD Out No Fee", "USD Fee", "fiat_ticker", "Notes"])

        in_writer.writeheader()
        out_writer.writeheader()

        for row in zenledger_reader:
            convert_row(row, in_writer, out_writer)

if __name__ == "__main__":
    convert_csv()
