import requests
import random


from django.core.exceptions import ObjectDoesNotExist

def generate_tracking_number():
    mylist=['1Z-0X6W74-12-9801050-9', '1Z-X62777-03-1002089-6', '1Z-3RA349-20-0158956-5','1Z-12345-01-9876-5432','1Z-ABC12-34-5678-90','1Z-XYZ99-88-7654-321','1Z-LMN11-22-3333-444','1Z-45678-90-9876-543']
    return random.choice (mylist)

def generate_ups_tracking_number():
    # UPS API endpoint for generating a tracking number
    ups_api_url = "https://onlinetools.ups.com/ship/v1/shipments"

    # UPS credentials (replace with your actual credentials)
    access_key = "your_access_key"
    username = "your_username"
    password = "your_password"

    # Create a request payload with the necessary information
    request_payload = {
        "ShipmentRequest": {
            "Request": {
                "RequestOption": "nonvalidate"
            },
            "Shipment": {
                # Add shipment details as needed
                "Shipper": {
                    "Name": "Your Company Name",
                    # Add shipper details
                },
                "ShipTo": {
                    # Add recipient details
                },
                # Add more shipment details
            },
        }
    }

    try:
        # Make a request to the UPS API
        response = requests.post(
            ups_api_url,
            json=request_payload,
            auth=(username, password),
            headers={"AccessLicenseNumber": access_key},
        )

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the UPS API response and extract the tracking number
            tracking_number = response.json().get("ShipmentResponse", {}).get(
                "ShipmentResults", {}).get("ShipmentIdentificationNumber")
            return tracking_number

        else:
            # Handle API request failure
            print(f"UPS API request failed with status code: {response.status_code}")

    except Exception as e:
        # Handle other exceptions
        print(f"An error occurred: {str(e)}")

    return None


