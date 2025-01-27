import streamlit as st
import pandas as pd
import logging
from pathlib import Path
import tempfile
from typing import Optional, Tuple
import sys
import io
import os

from pdf_to_txt import convert_pdf_to_text
from parser import parse_bank_statement, save_to_csv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set up directory structure
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdf"
CSV_DIR = DATA_DIR / "csv"

# Create directories if they don't exist
PDF_DIR.mkdir(parents=True, exist_ok=True)
CSV_DIR.mkdir(parents=True, exist_ok=True)

def save_uploaded_file(uploaded_file) -> Path:
    """Save uploaded file to PDF directory."""
    file_path = PDF_DIR / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def process_bank_statement(pdf_path: Path) -> pd.DataFrame:
    """
    Process a bank statement PDF file and return DataFrame.
    
    Args:
        pdf_path (Path): Path to the input PDF file
        
    Returns:
        pd.DataFrame: Processed DataFrame
    """
    # Create a temporary file in our data directory instead of system temp
    temp_path = DATA_DIR / f"temp_{pdf_path.stem}.txt"
    try:
        # Convert PDF to text
        convert_pdf_to_text(str(pdf_path), str(temp_path))
        
        # Read text content
        with open(temp_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        # Parse transactions
        transactions = parse_bank_statement(text_content)
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'Date': t.date.strftime("%d-%m-%y"),
                'Time': t.date.strftime("%H:%M"),
                'Channel': t.channel,
                'Details': t.details,
                'Transaction Type': t.transaction_type,
                'Recipient': t.recipient,
                'Amount': t.amount,
                'Balance': t.balance
            }
            for t in transactions
        ])
        
        return df
        
    finally:
        # Clean up temporary file
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete temporary file {temp_path}: {e}")

def get_excel_download_link(df: pd.DataFrame) -> bytes:
    """Generate Excel file bytes."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def main():
    st.set_page_config(
        page_title="Bank Statement Parser",
        page_icon="🏦",
        layout="wide"
    )
    
    st.title("🏦 Bank Statement Parser")
    st.write("Upload a bank statement PDF to convert it to a searchable table.")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file:
        try:
            # Save uploaded file
            with st.spinner("Saving uploaded file..."):
                pdf_path = save_uploaded_file(uploaded_file)
            
            # Process the statement
            with st.spinner("Processing bank statement..."):
                df = process_bank_statement(pdf_path)
                
                # Save CSV automatically
                csv_path = CSV_DIR / f"{pdf_path.stem}.csv"
                df.to_csv(csv_path, index=False)
            
            # Display success message
            st.success(f"Successfully processed {len(df)} transactions!")
            
            # Excel download button
            excel_data = get_excel_download_link(df)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"{pdf_path.stem}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # Display table
            st.subheader("Transaction Data")
            
            # Add search functionality
            search = st.text_input("🔍 Search transactions", "")
            if search:
                mask = df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
                filtered_df = df[mask]
            else:
                filtered_df = df
            
            # Display first 5000 rows
            st.dataframe(
                filtered_df.head(5000).style.format({
                    'Amount': '{:,.2f}',
                    'Balance': '{:,.2f}'
                }),
                use_container_width=True
            )
            
            # Display summary statistics
            st.subheader("Summary Statistics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Total Transactions",
                    len(df)
                )
            
            with col2:
                st.metric(
                    "Total Inbound",
                    f"฿{df[df['Amount'] > 0]['Amount'].sum():,.2f}"
                )
            
            with col3:
                st.metric(
                    "Total Outbound",
                    f"฿{abs(df[df['Amount'] < 0]['Amount'].sum()):,.2f}"
                )
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            logger.error(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()