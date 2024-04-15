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

def calculate_fee(row, asset_currency):
    if row["Fee Currency"] == "USD":
        return {"USD Fee": row["Fee Amount"]}
    elif row["Fee Currency"] == asset_currency:
        return {"Crypto Fee": row["Fee Amount"]}
    else:
        return {}

def prepare_fee_transaction(row, unique_id_suffix):
    return {
        "Unique ID": f"{row['Txid']}-{unique_id_suffix}",
        "Timestamp": format_timestamp(row["Timestamp"]),
        "Exchange": row["Exchange(optional)"],
        "Holder": "unknown",
        "Spot Price": "__unknown",  # Spot price unknown for fee-only transaction
        "Transaction Type": "Fee",
        "Asset": row["Fee Currency"],
        "USD Fee": row["Fee Amount"] if row["Fee Currency"] == "USD" else None,
        "Crypto Fee": row["Fee Amount"] if row["Fee Currency"] != "USD" else None,
        "Notes": "Fee transaction"
    }

def write_in_tx(row, in_writer, out_writer):
    transaction_type = type_map.get(row["Type"], "Unknown")
    asset_currency = row["IN Currency"]
    common_fields = prepare_common_fields(row, asset_currency)

    # Write the main in transaction
    in_writer.writerow({
        "Transaction Type": transaction_type,
        **common_fields,
        "Asset": asset_currency,
        "Crypto In": row["IN Amount"],
        "USD In No Fee": row["Out Amount"],
    })

def write_out_tx(row, out_writer):
    transaction_type = type_map.get(row["Type"], "Unknown")
    asset_currency = row["Out Currency"]
    common_fields = prepare_common_fields(row, asset_currency)

    # Write the main out transaction
    out_writer.writerow({
        "Transaction Type": transaction_type,
        **common_fields,
        "Asset": asset_currency,
        "Crypto Out No Fee": row["Out Amount"],
        "USD Out No Fee": row["IN Amount"],
    })

def write_fee_tx(row, in_writer, out_writer):
    if row["Fee Amount"] > 0:
        out_writer.writerow(prepare_fee_transaction(row))

def prepare_common_fields(row, asset_currency):
    fee_info = calculate_fee(row, asset_currency)
    return {
        "Unique ID": row["Txid"],
        "Timestamp": format_timestamp(row["Timestamp"]),
        "Exchange": row["Exchange(optional)"],
        "Holder": "unknown",  # not provided in the input
        "Spot Price": calculate_spot_price(row["IN Currency"], row["IN Amount"], row["Out Currency"], row["Out Amount"]),
        **fee_info
    }

def convert_csv():
    with open(args.zenledger_filename, "r", encoding="utf-8") as zenledger_file, \
         open(in_filename, "w", encoding="utf-8") as in_file, \
         open(out_filename, "w", encoding="utf-8") as out_file:

        # Set up CSV writers
        # Timestamp, Type, IN Amount, IN Currency, Out Amount, Out Currency, Fee Amount, Fee Currency, Exchange(optional), US Based, Txid
        zenledger_reader = csv.DictReader(zenledger_file)
        in_writer = csv.DictWriter(in_file, fieldnames=["Unique ID", "Timestamp", "Asset", "Exchange", "Holder", "Transaction Type", "Spot Price", "Crypto In", "Crypto Fee", "USD In No Fee", "USD In With Fee", "USD Fee", "Notes"])
        out_writer = csv.DictWriter(out_file, fieldnames=["Unique ID", "Timestamp", "Asset", "Exchange", "Holder", "Transaction Type", "Spot Price", "Crypto Out No Fee", "Crypto Fee", "Crypto Out With Fee", "USD Out No Fee", "USD Fee", "Notes"])

        in_writer.writeheader()
        out_writer.writeheader()

        for row in zenledger_reader:
            transaction_type = type_map.get(row["Type"], "Unknown")

            # Process trade transactions as two separate transactions (in and out), without duplicating fee
            if transaction_type == "trade":
                write_out_tx(row, out_writer)
                write_in_tx(row, in_writer, out_writer)
                write_fee_tx(row, in_writer, out_writer)
            elif transaction_type in ["Receive", "Buy", "Interest", "Staking"]:
                write_in_tx(row, in_writer, out_writer)
                write_fee_tx(row, in_writer, out_writer)
            elif transaction_type in ["Send", "Sell", "Fee"]:
                write_out_tx(row, out_writer)
                write_fee_tx(row, in_writer, out_writer)
            else: 
                print(f"Skipping unknown transaction type: {row['Type']}")

if __name__ == "__main__":
    convert_csv()
