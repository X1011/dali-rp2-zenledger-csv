import csv
from datetime import datetime

# Input and output file paths
zenledger_filename = "tx-zenledger_sample.csv"
in_filename    = "zenledger_manual_in.csv"
out_filename   = "zenledger_manual_out.csv"
intra_filename = "zenledger_manual_intra.csv"

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

def convert_csv():
    with open(zenledger_filename, "r", encoding="utf-8") as zenledger_file, \
         open(in_filename, "w", encoding="utf-8") as in_file, \
         open(out_filename, "w", encoding="utf-8") as out_file, \
         open(intra_filename, "w", encoding="utf-8") as intra_file:

        # Set up CSV writers
        # Timestamp, Type, IN Amount, IN Currency, Out Amount, Out Currency, Fee Amount, Fee Currency, Exchange(optional), US Based, Txid
        zenledger_reader = csv.DictReader(zenledger_file)
        in_writer = csv.DictWriter(in_file, fieldnames=["Unique ID", "Timestamp", "Asset", "Exchange", "Holder", "Transaction Type", "Spot Price", "Crypto In", "Crypto Fee", "USD In No Fee", "USD In With Fee", "USD Fee", "Notes"])
        out_writer = csv.DictWriter(out_file, fieldnames=["Unique ID", "Timestamp", "Asset", "Exchange", "Holder", "Transaction Type", "Spot Price", "Crypto Out No Fee", "Crypto Fee", "Crypto Out With Fee", "USD Out No Fee", "USD Fee", "Notes"])
        intra_writer = csv.DictWriter(intra_file, fieldnames=["Unique ID", "Timestamp", "Asset", "From Exchange", "From Holder", "To Exchange", "To Holder", "Spot Price", "Crypto Sent", "Crypto Received", "Notes"])

        in_writer.writeheader()
        out_writer.writeheader()
        intra_writer.writeheader()

        for row in zenledger_reader:
            timestamp = format_timestamp(row["Timestamp"])
            exchange = row["Exchange(optional)"]
            txid = row["Txid"]
            transaction_type = type_map.get(row["Type"], "Unknown")
            spot_price = calculate_spot_price(row["IN Currency"], row["IN Amount"], row["Out Currency"], row["Out Amount"])

            if transaction_type in ["Receive", "Buy", "Interest", "Staking"]:
                in_writer.writerow({
                    "Unique ID": txid,
                    "Timestamp": timestamp,
                    "Asset": row["IN Currency"],
                    "Exchange": exchange,
                    "Holder": "unknown",
                    "Transaction Type": transaction_type,
                    "Spot Price": spot_price,
                    "Crypto In": row["IN Amount"],
                    "Crypto Fee": row["Fee Amount"],
                    "USD In No Fee": row["Out Amount"],
                })
            elif transaction_type in ["Send", "Sell", "Fee"]:
                out_writer.writerow({
                    "Unique ID": txid,
                    "Timestamp": timestamp,
                    "Asset": row["Out Currency"],
                    "Exchange": exchange,
                    "Holder": "unknown",
                    "Transaction Type": transaction_type,
                    "Spot Price": spot_price,
                    "Crypto Out No Fee": row["Out Amount"],
                    "Crypto Fee": row["Fee Amount"],
                    "USD Out No Fee": row["IN Amount"],
                })
            elif transaction_type == "trade":  # Handle "trade" as Sell and Buy
                # Sell Transaction
                out_writer.writerow({
                    "Unique ID": txid,
                    "Timestamp": timestamp,
                    "Asset": row["Out Currency"],
                    "Exchange": exchange,
                    "Holder": "unknown", 
                    "Transaction Type": "Sell",
                    "Spot Price": "__unknown",
                    "Crypto Out No Fee": row["Out Amount"],
                    "Crypto Fee": row["Fee Amount"],  # Assuming fee is in the "out" currency
                    "USD Fee": "",  # No fiat_fee
                    "Notes": "Trade: Sell side"
                })

                # Buy Transaction
                in_writer.writerow({
                    "Unique ID": f"{txid}/buy",  # Unique ID with suffix to distinguish
                    "Timestamp": timestamp,
                    "Asset": row["IN Currency"],
                    "Exchange": exchange,
                    "Holder": "unknown",
                    "Transaction Type": "Buy",
                    "Spot Price": "__unknown",
                    "Crypto In": row["IN Amount"],
                    "Crypto Fee": "",  # No crypto fee for buy side
                    "USD Fee": "",  # No fiat_fee
                    "Notes": "Trade: Buy side"
                })
            else: 
                print(f"Skipping unknown transaction type: {row['Type']}")

if __name__ == "__main__":
    convert_csv()


