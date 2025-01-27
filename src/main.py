import argparse
import logging
from pathlib import Path
import tempfile
from typing import Optional
import sys

from pdf_to_txt import convert_pdf_to_text
from parser import parse_bank_statement, save_to_csv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_bank_statement(
    pdf_path: str,
    output_path: Optional[str] = None,
    keep_text: bool = False
) -> None:
    """
    Process a bank statement PDF file and convert it to CSV.
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_path (Optional[str]): Path for output CSV file. If None, uses input filename
        keep_text (bool): Whether to keep the intermediate text file
    """
    try:
        pdf_path = Path(pdf_path)
        
        # Validate input file
        if not pdf_path.exists():
            raise FileNotFoundError(f"Input file not found: {pdf_path}")
        
        if pdf_path.suffix.lower() != '.pdf':
            raise ValueError(f"Input file must be a PDF: {pdf_path}")
        
        # Set up output path
        if output_path:
            output_csv = Path(output_path)
        else:
            output_csv = pdf_path.with_suffix('.csv')
        
        # Create temporary directory for text file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up text file path
            text_path = Path(temp_dir) / f"{pdf_path.stem}.txt"
            if keep_text:
                text_path = pdf_path.with_suffix('.txt')
            
            logger.info(f"Converting PDF to text: {pdf_path}")
            convert_pdf_to_text(str(pdf_path), str(text_path))
            
            logger.info("Reading text content")
            with open(text_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            logger.info("Parsing bank statement")
            transactions = parse_bank_statement(text_content)
            
            logger.info(f"Saving {len(transactions)} transactions to CSV")
            save_to_csv(transactions, str(output_csv))
            
            logger.info(f"Processing complete. Output saved to: {output_csv}")
            
            if keep_text:
                logger.info(f"Text file saved to: {text_path}")
    
    except Exception as e:
        logger.error(f"Error processing bank statement: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(
        description='Convert bank statement PDF to CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py statement.pdf
    python main.py statement.pdf -o output.csv
    python main.py statement.pdf --keep-text
        """
    )
    
    parser.add_argument(
        'pdf_path',
        help='Path to the bank statement PDF file'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Path for output CSV file (default: same as input with .csv extension)'
    )
    
    parser.add_argument(
        '--keep-text',
        action='store_true',
        help='Keep the intermediate text file'
    )
    
    args = parser.parse_args()
    
    try:
        process_bank_statement(
            args.pdf_path,
            args.output,
            args.keep_text
        )
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()