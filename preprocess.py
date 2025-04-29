import pandas as pd

# Load Violation Code mappings from Excel
violation_codes_df = pd.read_excel("data/ParkingViolationCodes_January2020.xlsx")
VIOLATION_CODE_TO_DESC = dict(zip(violation_codes_df["VIOLATION CODE"], violation_codes_df["VIOLATION DESCRIPTION"]))
VIOLATION_CODE_TO_FINE = dict(
    zip(violation_codes_df["VIOLATION CODE"], violation_codes_df["All Other Areas\n(Fine Amount $)"]))


def discretize_fine(amount):
    if amount < 50:
        return "Low Fine"
    elif 50 <= amount <= 100:
        return "Medium Fine"
    else:
        return "High Fine"


def discretize_time(time_str):
    try:
        if not isinstance(time_str, str) or not time_str:
            return "Unknown Time"
        time_str = time_str.strip()

        # Handle formats like "0730A" or "0730P"
        if len(time_str) >= 5 and time_str[-1] in ['A', 'P']:
            time_clean = f"{time_str[:2]}:{time_str[2:4]} {'AM' if time_str[-1] == 'A' else 'PM'}"
        elif ":" in time_str:
            time_clean = time_str
        else:
            return "Unknown Time"

        hour = pd.to_datetime(time_clean, format="%H:%M %p", errors="coerce").hour
        if pd.isna(hour):
            hour = pd.to_datetime(time_clean, format="%H:%M", errors="coerce").hour
        if pd.isna(hour):
            print(f"Failed to parse time: {time_str}")
            return "Unknown Time"

        if 6 <= hour < 12:
            return "Morning"
        elif 12 <= hour < 18:
            return "Afternoon"
        elif 18 <= hour < 24:
            return "Evening"
        else:
            return "Night"
    except Exception as e:
        print(f"Error parsing time '{time_str}': {e}")
        return "Unknown Time"


def standardize_vehicle_type(vehicle_type):
    if not isinstance(vehicle_type, str) or not vehicle_type:
        return "Unknown Vehicle"
    vehicle_type = vehicle_type.upper()
    vehicle_map = {
        'SDN': 'Sedan', '2DSD': 'Sedan', '4DSD': 'Sedan',
        'SUBN': 'SUV', 'PICK': 'Pickup', 'VAN': 'Van'
    }
    return vehicle_map.get(vehicle_type, "Other Vehicle")


def map_county_to_borough(county):
    if not isinstance(county, str):
        return None
    county = county.upper()
    county_to_borough = {
        'NY': 'Manhattan', 'K': 'Brooklyn', 'Q': 'Queens',
        'BX': 'Bronx', 'R': 'Staten Island',
        'BRONX': 'Bronx', 'BROOKLYN': 'Brooklyn', 'QUEENS': 'Queens',
        'MANHATTAN': 'Manhattan', 'STATEN ISLAND': 'Staten Island'
    }
    return county_to_borough.get(county, None)


def preprocess():
    parking = pd.read_csv("data/parking_first_march_2025.csv", low_memory=False)

    parking['Issue Date'] = pd.to_datetime(parking['Issue Date'], format='%m/%d/%Y', errors='coerce')
    parking = parking.dropna(subset=['Issue Date'])

    parking["Time Period"] = parking["Violation Time"].apply(discretize_time)

    parking["Fine Amount"] = parking["Violation Code"].map(VIOLATION_CODE_TO_FINE).fillna(0)
    parking["Fine Level"] = parking["Fine Amount"].apply(discretize_fine)

    parking["Vehicle Type"] = parking["Vehicle Body Type"].apply(standardize_vehicle_type)

    parking["Borough"] = parking["Violation County"].apply(map_county_to_borough)

    parking["Violation Description"] = parking["Violation Code"].map(VIOLATION_CODE_TO_DESC)

    parking = parking.dropna(subset=['Borough', 'Fine Amount', 'Violation Description'])

    transactions = []
    for _, row in parking.iterrows():
        ordered_items = [
            row["Borough"],
            row["Time Period"],
            row["Fine Level"],
            row["Vehicle Type"],
            str(row["Violation Code"]),
            row["Violation Description"]
        ]

        if any(item is None or not item for item in ordered_items):
            continue
        if row["Vehicle Type"] in ["Other Vehicle", "Unknown Vehicle"]:
            continue
        valid_items = [item for item in ordered_items if "Unknown" not in item and "Other" not in item]
        if len(valid_items) < 4:
            continue
        transactions.append(",".join(ordered_items))

    with open("INTEGRATED-DATASET.csv", "w") as f:
        f.write("\n".join(transactions))


if __name__ == "__main__":
    preprocess()