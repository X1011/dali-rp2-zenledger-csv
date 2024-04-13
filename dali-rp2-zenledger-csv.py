import csv
from datetime import datetime

# Input and output file paths
ZENLEDGER_CSV_PATH = "tx-zenledger_sample.csv"
DALI_IN_CSV_PATH = "dali_manual_in.csv"
DALI_OUT_CSV_PATH = "dali_manual_out.csv"
DALI_INTRA_CSV_PATH = "dali_manual_intra.csv"

# Mapping ZenLedger transaction types to DaLI transaction types
TYPE_MAPPING = {
    "Receive": "Deposit",
    "buy": "Buy",
    "dividend_received": "Interest",
    "fee": "Fee",
    "sell": "Sell",
    "staking_reward": "Staking",
    "trade": "Sell",  # Assuming trade is a sell for simplicity
    "Send": "Move",
}

def convert_csv():
    with open(ZENLEDGER_CSV_PATH, "r", encoding="utf-8") as zenledger_file, \
         open(DALI_IN_CSV_PATH, "w", encoding="utf-8") as dali_in_file, \
         open(DALI_OUT_CSV_PATH, "w", encoding="utf-8") as dali_out_file, \
         open(DALI_INTRA_CSV_PATH, "w", encoding="utf-8") as dali_intra_file:

        # Set up CSV writers
        zenledger_reader = csv.DictReader(zenledger_file)
        dali_in_writer = csv.writer(dali_in_file)
        dali_out_writer = csv.writer(dali_out_file)
        dali_intra_writer = csv.writer(dali_intra_file)

        # Write header rows for DaLI CSVs
        dali_in_writer.writerow(["Unique ID", "Timestamp", "Asset", "Exchange", "Holder", "Transaction Type", "Spot Price", "Crypto In", "Crypto Fee", "USD In No Fee", "USD In With Fee", "USD Fee", "Notes"])
        dali_out_writer.writerow(["Unique ID", "Timestamp", "Asset", "Exchange", "Holder", "Transaction Type", "Spot Price", "Crypto Out No Fee", "Crypto Fee", "Crypto Out With Fee", "USD Out No Fee", "USD Fee", "Notes"])
        dali_intra_writer.writerow(["Unique ID", "Timestamp", "Asset", "From Exchange", "From Holder", "To Exchange", "To Holder", "Spot Price", "Crypto Sent", "Crypto Received", "Notes"])

        for row in zenledger_reader:
            # Handle the 'Z' at the end of the timestamp
            if row["Timestamp"].endswith("Z"):
                timestamp_value = datetime.fromisoformat(row["Timestamp"][:-1] + "+00:00")
            else:
                timestamp_value = datetime.fromisoformat(row["Timestamp"])
            timestamp = timestamp_value.strftime("%Y-%m-%d %H:%M:%S%z")
            exchange = row["Exchange(optional)"]
            txid = row["Txid"]
            transaction_type = TYPE_MAPPING.get(row["Type"], "Unknown")

            # Calculate spot price if one currency is USD
            if row["IN Currency"] == "USD":
                spot_price = str(float(row["IN Amount"]) / float(row["Out Amount"])) 
            elif row["Out Currency"] == "USD":
                spot_price = str(float(row["Out Amount"]) / float(row["IN Amount"]))
            else:
                spot_price = "__unknown"

            if transaction_type in ["Buy", "Interest", "Staking", "Deposit"]:
                dali_in_writer.writerow([
                    txid,
                    timestamp,
                    row["IN Currency"],
                    exchange,
                    "unknown",  # Assuming holder is unknown 
                    transaction_type,
                    spot_price,
                    row["IN Amount"],
                    row["Fee Amount"],
                    row["Out Amount"],
                    "",
                    "",
                    ""
                ])
            elif transaction_type in ["Sell", "Fee"]:
                dali_out_writer.writerow([
                    txid,
                    timestamp,
                    row["Out Currency"],
                    exchange,
                    "unknown",  # Assuming holder is unknown 
                    transaction_type,
                    spot_price,
                    row["Out Amount"],
                    row["Fee Amount"],
                    "",
                    row["IN Amount"],
                    "",
                    ""
                ])
            elif transaction_type == "Move":
                dali_intra_writer.writerow([
                    txid,
                    timestamp,
                    row["Out Currency"],
                    exchange,
                    "unknown",  # Assuming holder is unknown 
                    "unknown",  # Assuming destination exchange is unknown 
                    "unknown",  # Assuming destination holder is unknown 
                    spot_price,
                    row["Out Amount"],
                    row["IN Amount"],
                    ""
                ])
            else: 
                print(f"Skipping unknown transaction type: {row['Type']}")

if __name__ == "__main__":
    convert_csv()


