# --- Step 1: Install Necessary Libraries ---
# This command installs the required Python packages.
# IMPORTANT: Run 'pip install requests pandas sec-api' in your terminal/Cloud Shell BEFORE running this script.

# --- Step 2: Import Modules ---
import requests
import json
import time
from datetime import datetime
import pandas as pd
from sec_api import InsiderTradingApi # Directly using InsiderTradingApi for parsed data
import sys
import traceback # Import traceback for detailed error reporting

# --- Step 3: Configuration ---
# Your User-Agent for general web requests.
USER_AGENT = "StevenDayApp/1.0 (sday75@gmail.com)"

# Your sec-api.io API Key.
# IMPORTANT: Keep this key confidential and do not share it publicly.
SEC_API_KEY = "6fa876e5977a37da9b6e5a210ee6faf20e63a2ef5b10e1e8b3271d005c15f3c5"

# --- Step 4: Main Program Logic ---
def main():
    print("--- PROGRAM STARTING: Form 4 Sales ('S' Code) Transaction Summary (with Total Sale Value and Percentage) ---")

    # Initialize the InsiderTradingApi client with your API key
    try:
        insiderTradingApi = InsiderTradingApi(api_key=SEC_API_KEY)
    except Exception as e:
        print(f"\nERROR: Could not initialize InsiderTradingApi with provided key.")
        print(f"Details: {e}")
        print("Please ensure your API_KEY is correct and the 'sec-api' library is installed.")
        return

    # 1. Get user input for the filing date
    while True:
        date_input = input("Enter the filing date (YYYY-MM-DD, e.g., 2024-01-15): ")
        try:
            target_date = datetime.strptime(date_input, '%Y-%m-%d').date()
            break # Exit loop if date format is valid
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

    date_str = target_date.strftime('%Y-%m-%d')
    print(f"\nSearching for ALL Form 4 insider transactions filed on: {date_str} using sec-api.io's InsiderTradingApi...")

    # Pagination parameters
    current_from = 0
    page_size = 50 # Max size allowed by sec-api.io InsiderTradingApi
    total_filings_reported = -1 # Initialize to -1 to ensure first loop runs
    all_raw_filings_from_api = [] # To store raw filing objects from each page

    print(f"Fetching filings in pages of {page_size}...")

    try: # Start the main try block to catch errors during fetching and processing
        while total_filings_reported == -1 or current_from < total_filings_reported:
            query_params = {
                "query": f'documentType:4 AND filedAt:[{date_str} TO {date_str}]',
                "from": str(current_from), # 'from' parameter must be a string
                "size": str(page_size),    # 'size' parameter must be a string
                "sort": [{ "filedAt": { "order": "asc" } }]
            }

            try: # Inner try block for individual API calls
                response_data = insiderTradingApi.get_data(query_params)

                if isinstance(response_data, dict) and 'error' in response_data:
                    print("\n---------------------------------------------------")
                    print("API Call Result: FAILED (API returned an error during pagination).")
                    print(f"Error Details: {json.dumps(response_data['error'], indent=2)}")
                    print("This usually indicates an issue with the API key, rate limits, or a critical service issue.")
                    print("Please double-check your API key and review your sec-api.io account dashboard.")
                    print("---------------------------------------------------")
                    return

                filings_on_page = response_data.get('transactions', []) # InsiderTradingApi returns 'transactions' at top-level
                total_filings_reported_on_page = response_data.get('total', {}).get('value', 0)

                if total_filings_reported == -1: # Set total filings on the first successful call
                    total_filings_reported = total_filings_reported_on_page
                    print(f"Total Form 4 filings reported by API for {date_str}: {total_filings_reported}")
                    if total_filings_reported == 0:
                        print(f"No Form 4 filings found for {date_str}. Exiting.")
                        return

                if not filings_on_page:
                    print(f"No more filings found from 'from': {current_from}. Ending pagination.")
                    break # No more filings to fetch

                all_raw_filings_from_api.extend(filings_on_page)
                print(f"Fetched {len(filings_on_page)} filings (total fetched: {len(all_raw_filings_from_api)}/{total_filings_reported}).")

                current_from += page_size
                time.sleep(0.1) # Be polite to the API, 10 requests per second max

            except requests.exceptions.HTTPError as e:
                print("\n---------------------------------------------------")
                print(f"API Call Result: FAILED (HTTP Error encountered during pagination).")
                print(f"Status Code: {e.response.status_code}")
                print(f"Response Text from sec-api.io: {e.response.text}")
                print("This typically indicates issues like invalid API key, exceeded rate limits, or a problem with your subscription tier.")
                print("Please verify your API key and check your account dashboard for usage and status.")
                print("---------------------------------------------------")
                return
            except requests.exceptions.RequestException as e:
                print("\n---------------------------------------------------")
                print(f"API Call Result: FAILED (Network or connection error during pagination).")
                print(f"Details: {e}")
                print("This could be due to a lost internet connection or a temporary issue with sec-api.io's servers.")
                print("Please ensure you have a stable internet connection and try running the program again later.")
                print("------------------------------------------------------------------------------------------------")
                return
            except Exception as e:
                print("\n---------------------------------------------------")
                print(f"API Call Result: FAILED (An unexpected error occurred during pagination).")
                print(f"Details: {e}")
                print("This might be a bug in the program or an unusual response from the API.")
                print("---------------------------------------------------")
                # Print full traceback for detailed debugging
                traceback.print_exc()
                return

        if not all_raw_filings_from_api:
            print(f"\nNo Form 4 filings found for {date_str} after all attempts.")
            print("This could mean no companies filed Form 4s on this day, or there's a persistent issue.")
            return

        print(f"\nSuccessfully retrieved a total of {len(all_raw_filings_from_api)} Form 4 filings for {date_str}.")
        print("\n--- Extracting All Available Parsed Data from Table I & II ---")

        all_parsed_transactions = []

        for filing in all_raw_filings_from_api:
            # Extract common filing-level information once per filing
            issuer_info = filing.get('issuer', {})
            reporting_owner_info = filing.get('reportingOwner', {})

            # General filing details
            filing_common_data = {
                'Transaction ID': filing.get('id', 'N/A'),
                'Accession Number': filing.get('accessionNo', 'N/A'),
                'Filed At': filing.get('filedAt', 'N/A'),
                'Form Type': filing.get('documentType', 'N/A'), # Use documentType from top-level
                'Period of Report': filing.get('periodOfReport', 'N/A'),
                'Not Subject to Section 16': filing.get('notSubjectToSection16', 'N/A'),

                'Issuer Name (Box 2)': issuer_info.get('name', 'N/A'),
                'Issuer Ticker': issuer_info.get('tradingSymbol', 'N/A'),
                'Issuer CIK': issuer_info.get('cik', 'N/A'),

                'Reporting Person Name (Box 1)': reporting_owner_info.get('name', 'N/A'),
                'Reporting Person CIK': reporting_owner_info.get('cik', 'N/A'),
            }

            # Relationship details (Box 5)
            relationship = reporting_owner_info.get('relationship', {})
            is_director = relationship.get('isDirector', False)
            is_officer = relationship.get('isOfficer', False)
            officer_title = relationship.get('officerTitle', '')
            is_ten_percent_owner = relationship.get('isTenPercentOwner', False)
            is_other = relationship.get('isOther', False)
            other_text = relationship.get('otherText', 'N/A')

            filing_common_data['Is Director (Box 5)'] = is_director
            filing_common_data['Is Officer (Box 5)'] = is_officer
            filing_common_data['Is 10% Owner (Box 5)'] = is_ten_percent_owner
            filing_common_data['Is Other Relationship (Box 5)'] = is_other
            filing_common_data['Other Relationship Text (Box 5)'] = other_text

            # Determine the value for the 'Officer Title (Box 5)' column based on the new logic
            if is_director:
                filing_common_data['Officer Title (Box 5)'] = "Director"
            elif is_ten_percent_owner:
                filing_common_data['Officer Title (Box 5)'] = "10% Owner"
            elif is_officer and officer_title:
                filing_common_data['Officer Title (Box 5)'] = officer_title
            else:
                filing_common_data['Officer Title (Box 5)'] = "N/A" # Fallback if none of the above are true or officerTitle is empty

            # Reporting Owner Address (optional)
            address = reporting_owner_info.get('address', {})
            filing_common_data['Owner Address Street1'] = address.get('street1', 'N/A')
            filing_common_data['Owner Address Street2'] = address.get('street2', 'N/A')
            filing_common_data['Owner Address City'] = address.get('city', 'N/A')
            filing_common_data['Owner Address Zip Code'] = address.get('zipCode', 'N/A')
            filing_common_data['Owner Address State'] = address.get('stateDescription', 'N/A')

            # Ownership Nature
            ownership_nature = filing.get('ownershipNature', {}) # Ownership nature can be at filing level or transaction level
            filing_common_data['Direct/Indirect Ownership (Filing)'] = ownership_nature.get('directOrIndirectOwnership', 'N/A')
            filing_common_data['Nature of Ownership (Filing)'] = ownership_nature.get('natureOfOwnership', 'N/A')

            filing_common_data['Filing URL'] = filing.get('linkToFiling', 'N/A')

            # --- Process Non-Derivative Transactions (Table I) ---
            non_derivative_table = filing.get('nonDerivativeTable', {})
            non_derivative_transactions_list = non_derivative_table.get('transactions', [])

            for transaction in non_derivative_transactions_list:
                current_transaction_data = filing_common_data.copy() # Start with common data
                current_transaction_data['Transaction Table'] = 'Table I (Non-Derivative)'

                # Table I specific fields
                current_transaction_data['Security Title'] = transaction.get('securityTitle', 'N/A')
                current_transaction_data['Transaction Date'] = transaction.get('transactionDate', 'N/A')
                current_transaction_data['Deemed Execution Date'] = transaction.get('deemedExecutionDate', 'N/A')

                coding = transaction.get('coding', {})
                current_transaction_data['Transaction Code'] = coding.get('code', 'N/A')
                current_transaction_data['Equity Swap Involved'] = coding.get('equitySwapInvolved', 'N/A')
                current_transaction_data['Transaction Footnote ID'] = coding.get('footnoteId', 'N/A')
                current_transaction_data['Timeliness'] = coding.get('timeliness', 'N/A')

                amounts = transaction.get('amounts', {})
                current_transaction_data['Shares Acquired/Disposed'] = amounts.get('shares', 'N/A')
                current_transaction_data['Price Per Share'] = amounts.get('pricePerShare', 'N/A')
                current_transaction_data['Acquired/Disposed Code'] = amounts.get('acquiredDisposedCode', 'N/A')

                post_transaction_amounts = transaction.get('postTransactionAmounts', {})
                current_transaction_data['Shares Owned Following Transaction'] = post_transaction_amounts.get('sharesOwnedFollowingTransaction', 'N/A')
                current_transaction_data['Value Owned Following Transaction'] = post_transaction_amounts.get('valueOwnedFollowingTransaction', 'N/A')

                # Ownership Nature (can be at transaction level, override filing level if present)
                trans_ownership_nature = transaction.get('ownershipNature', {})
                current_transaction_data['Direct/Indirect Ownership (Transaction)'] = trans_ownership_nature.get('directOrIndirectOwnership', 'N/A')
                current_transaction_data['Nature of Ownership (Transaction)'] = trans_ownership_nature.get('natureOfOwnership', 'N/A')

                # Fields specific to Derivative (set to N/A for Table I)
                current_transaction_data['Conversion/Exercise Price'] = 'N/A'
                current_transaction_data['Exercise Date'] = 'N/A'
                current_transaction_data['Expiration Date'] = 'N/A'
                current_transaction_data['Underlying Security Title'] = 'N/A'
                current_transaction_data['Underlying Security Shares'] = 'N/A'
                current_transaction_data['Underlying Security Value'] = 'N/A'

                all_parsed_transactions.append(current_transaction_data)
                time.sleep(0.01) # Small delay

            # Process Derivative Transactions (Table II)
            derivative_table = filing.get('derivativeTable', {})
            derivative_transactions_list = derivative_table.get('transactions', [])

            for transaction in derivative_transactions_list:
                current_transaction_data = filing_common_data.copy() # Start with common data
                current_transaction_data['Transaction Table'] = 'Table II (Derivative)'

                # Table II specific fields
                current_transaction_data['Security Title'] = transaction.get('securityTitle', 'N/A')
                current_transaction_data['Transaction Date'] = transaction.get('transactionDate', 'N/A')
                current_transaction_data['Deemed Execution Date'] = transaction.get('deemedExecutionDate', 'N/A')
                current_transaction_data['Conversion/Exercise Price'] = transaction.get('conversionOrExercisePrice', 'N/A')
                current_transaction_data['Exercise Date'] = transaction.get('exerciseDate', 'N/A')
                current_transaction_data['Expiration Date'] = transaction.get('expirationDate', 'N/A')

                coding = transaction.get('coding', {})
                current_transaction_data['Transaction Code'] = coding.get('code', 'N/A')
                current_transaction_data['Equity Swap Involved'] = coding.get('equitySwapInvolved', 'N/A')
                current_transaction_data['Transaction Footnote ID'] = coding.get('footnoteId', 'N/A')
                current_transaction_data['Timeliness'] = coding.get('timeliness', 'N/A')

                amounts = transaction.get('amounts', {})
                # Note: For derivative transactions, 'shares' and 'pricePerShare' in 'amounts' refer to the derivative itself
                current_transaction_data['Shares Acquired/Disposed (Derivative)'] = amounts.get('shares', 'N/A')
                current_transaction_data['Price Per Share (Derivative)'] = amounts.get('pricePerShare', 'N/A')
                current_transaction_data['Acquired/Disposed Code (Derivative)'] = amounts.get('acquiredDisposedCode', 'N/A')

                underlying_security = transaction.get('underlyingSecurity', {})
                current_transaction_data['Underlying Security Title'] = underlying_security.get('title', 'N/A')
                current_transaction_data['Underlying Security Shares'] = underlying_security.get('shares', 'N/A')
                current_transaction_data['Underlying Security Value'] = underlying_security.get('value', 'N/A')

                post_transaction_amounts = transaction.get('postTransactionAmounts', {})
                current_transaction_data['Shares Owned Following Transaction'] = post_transaction_amounts.get('sharesOwnedFollowingTransaction', 'N/A')
                current_transaction_data['Value Owned Following Transaction'] = post_transaction_amounts.get('valueOwnedFollowingTransaction', 'N/A')

                # Ownership Nature (can be at transaction level, override filing level if present)
                trans_ownership_nature = transaction.get('ownershipNature', {})
                current_transaction_data['Direct/Indirect Ownership (Transaction)'] = trans_ownership_nature.get('directOrIndirectOwnership', 'N/A')
                current_transaction_data['Nature of Ownership (Transaction)'] = trans_ownership_nature.get('natureOfOwnership', 'N/A')

                # Fields specific to Non-Derivative (set to N/A for Table II)
                current_transaction_data['Shares Acquired/Disposed'] = 'N/A' # This was for non-derivative shares
                current_transaction_data['Price Per Share'] = 'N/A' # This was for non-derivative price
                current_transaction_data['Acquired/Disposed Code'] = 'N/A' # This was for non-derivative code

                all_parsed_transactions.append(current_transaction_data)
                time.sleep(0.01) # Small delay

    except requests.exceptions.HTTPError as e:
        print("\n---------------------------------------------------")
        print(f"HTTP Error encountered: Status Code {e.response.status_code}")
        print(f"Response Text from sec-api.io: {e.response.text}")
        print("This typically indicates issues like an invalid API key, exceeded rate limits, or a problem with your subscription tier.")
        print("Please verify your API key and check your account dashboard for usage and status.")
        print("---------------------------------------------------")
        return
    except requests.exceptions.RequestException as e:
        print("\n---------------------------------------------------")
        print(f"Network or connection error: {e}")
        print("This could be due to a lost internet connection or a temporary issue with sec-api.io's servers.")
        print("Please ensure you have a stable internet connection and try running the program again later.")
        print("------------------------------------------------------------------------------------------------")
        return
    except Exception as e:
        print("\n---------------------------------------------------")
        print(f"An unexpected error occurred during API interaction or data processing: {e}")
        print("This might be a bug in the program or an unusual response from the API.")
        print("---------------------------------------------------")
        # Print full traceback for detailed debugging
        traceback.print_exc()
        return


    # If no transactions were parsed after attempting to process
    if not all_parsed_transactions:
        print("\nNo detailed transaction summaries could be extracted for the specified date.")
        print("This is highly unusual for a full access account if filings exist for the date. Please contact sec-api.io support.")
        return

    # --- Step 5: Data Processing and Summarization with Pandas ---
    df = pd.DataFrame(all_parsed_transactions)

    # Convert date columns to datetime objects for proper sorting and then back to string
    date_columns = ['Filed At', 'Period of Report', 'Transaction Date', 'Deemed Execution Date', 'Exercise Date', 'Expiration Date']
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d').fillna('N/A') # Use N/A for invalid dates

    # Sort by Issuer, Transaction Table, and then Transaction Date for better readability
    df = df.sort_values(by=['Issuer Name (Box 2)', 'Transaction Table', 'Transaction Date']).reset_index(drop=True)

    # --- Filter for Transaction Code "S" (Sale) ---
    sales_df = df[df['Transaction Code'] == 'S'].copy()

    if sales_df.empty:
        print(f"\nNo 'S' (Sale) transactions found for {date_str}.")
        print("\nPROGRAM FINISHED SUCCESSFULLY (No sales found)!")
        return

    # Create unified 'Shares Sold' and 'Price Per Share' columns
    # These columns will pick the non-N/A value from the derivative/non-derivative specific columns
    sales_df['Shares Sold'] = sales_df['Shares Acquired/Disposed'].fillna(sales_df['Shares Acquired/Disposed (Derivative)'])
    sales_df['Price Per Share'] = sales_df['Price Per Share'].fillna(sales_df['Price Per Share (Derivative)'])

    # Convert to numeric, coercing errors to NaN, then fill NaN with 0 for calculations if needed
    sales_df['Shares Sold'] = pd.to_numeric(sales_df['Shares Sold'], errors='coerce').fillna(0)
    sales_df['Price Per Share'] = pd.to_numeric(sales_df['Price Per Share'], errors='coerce').fillna(0)

    # Convert 'Shares Owned Following Transaction' to numeric for calculation
    sales_df['Shares Owned Following Transaction'] = pd.to_numeric(sales_df['Shares Owned Following Transaction'], errors='coerce').fillna(0)

    # --- Calculate "Percentage of Holdings Sold" ---
    # Denominator: Shares Owned Following Transaction + Shares Sold
    denominator = sales_df['Shares Owned Following Transaction'] + sales_df['Shares Sold']

    # Handle division by zero: if denominator is 0, result is 0 or NaN
    # Calculate as a float first
    sales_df['Percentage of Holdings Sold'] = sales_df['Shares Sold'] / denominator
    # Fill NaN (from 0/0) with 0, then format as percentage string
    sales_df['Percentage of Holdings Sold'] = sales_df['Percentage of Holdings Sold'].fillna(0).apply(lambda x: f"{x:.2%}")

    # --- Calculate "Total Sale Value" ---
    sales_df['Total Sale Value'] = sales_df['Shares Sold'] * sales_df['Price Per Share']
    # Format Total Sale Value as currency string
    sales_df['Total Sale Value'] = sales_df['Total Sale Value'].apply(lambda x: f"${x:,.2f}")


    print("\n--- Summary of Form 4 'S' (Sale) Transactions ---")
    # Select and display the requested columns
    summary_columns = [
        'Reporting Person Name (Box 1)',
        'Officer Title (Box 5)', # This column's logic is now enhanced
        'Issuer Name (Box 2)',
        'Shares Sold',
        'Price Per Share',
        'Total Sale Value',
        'Transaction Date', # Add transaction date for context
        'Transaction Table', # To see if it was derivative or non-derivative
        'Percentage of Holdings Sold',
        'Filing URL'
    ]

    # Ensure all summary columns exist before trying to display
    summary_df = sales_df[sales_df.columns.intersection(summary_columns)]

    # For displaying in markdown, we can't use floatfmt for specific columns
    # since 'Percentage of Holdings Sold' and 'Total Sale Value' are now strings.
    # We will print it directly.
    print(summary_df.to_markdown(index=False))

    # --- Save Results to CSV ---
    try:
        output_filename_csv = f"form4_sales_summary_{target_date.strftime('%Y-%m-%d')}.csv"
        # For CSV, we want the raw numeric percentage and value, not the formatted string.
        # So, create a temporary df for CSV saving with the numeric percentage and value.
        temp_df_for_csv = sales_df[sales_df.columns.intersection(summary_columns)].copy()

        # Revert 'Percentage of Holdings Sold' to numeric for CSV
        temp_df_for_csv['Percentage of Holdings Sold'] = pd.to_numeric(sales_df['Shares Sold'], errors='coerce') / (pd.to_numeric(sales_df['Shares Owned Following Transaction'], errors='coerce') + pd.to_numeric(sales_df['Shares Sold'], errors='coerce'))
        temp_df_for_csv['Percentage of Holdings Sold'] = temp_df_for_csv['Percentage of Holdings Sold'].fillna(0) # Fill NaN (from 0/0) with 0

        # Revert 'Total Sale Value' to numeric for CSV
        temp_df_for_csv['Total Sale Value'] = pd.to_numeric(sales_df['Shares Sold'], errors='coerce') * pd.to_numeric(sales_df['Price Per Share'], errors='coerce')
        temp_df_for_csv['Total Sale Value'] = temp_df_for_csv['Total Sale Value'].fillna(0)

        temp_df_for_csv.to_csv(output_filename_csv, index=False)
        print(f"\nSales transaction summaries saved to CSV: {output_filename_csv}")

        # --- Save to JSON for Website ---
        output_filename_json = "form4_sales_data.json"
        # Convert DataFrame to a list of dictionaries (JSON format)
        # The JSON will contain the formatted percentage string and total sale value string for direct use by the website.
        summary_df.to_json(output_filename_json, orient='records', indent=4)
        print(f"Sales transaction data saved to JSON for website: {output_filename_json}")

        print("You can download these files from the Colab 'Files' tab (folder icon on the left sidebar).")
        print("\nPROGRAM FINISHED SUCCESSFULLY!")

    except Exception as e:
        print(f"Error saving data to CSV/JSON: {e}")

# --- Step 7: Call the main function to run the program ---
if __name__ == "__main__":
    main()
