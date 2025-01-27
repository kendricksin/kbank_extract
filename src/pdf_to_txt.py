import os
import PyPDF2
import argparse
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_pdf_to_text(pdf_path: str, output_path: str) -> None:
    """
    Convert a PDF file to text and save it to the specified output path.
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_path (str): Path where the text file should be saved
    """
    try:
        # Open the PDF file
        with open(pdf_path, 'rb') as pdf_file:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from each page
            text_content = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content.append(page.extract_text())
            
            # Join all pages with a newline
            full_text = '\n'.join(text_content)
            
            # Write the text to the output file
            with open(output_path, 'w', encoding='utf-8') as text_file:
                text_file.write(full_text)
                
            logger.info(f"Successfully converted {pdf_path} to text")
            logger.info(f"Text file saved at: {output_path}")
            
    except Exception as e:
        logger.error(f"Error converting {pdf_path}: {str(e)}")
        raise

def process_directory(input_dir: str, output_dir: str) -> None:
    """
    Process all PDF files in the input directory and save text files to output directory.
    
    Args:
        input_dir (str): Directory containing PDF files
        output_dir (str): Directory where text files should be saved
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files in the input directory
    pdf_files = Path(input_dir).glob('*.pdf')
    
    # Process each PDF file
    for pdf_path in pdf_files:
        # Create output path with same name but .txt extension
        output_path = Path(output_dir) / f"{pdf_path.stem}.txt"
        
        try:
            convert_pdf_to_text(str(pdf_path), str(output_path))
        except Exception as e:
            logger.error(f"Failed to process {pdf_path}: {str(e)}")
            continue

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Convert PDF files to text')
    parser.add_argument('input_path', help='Path to PDF file or directory')
    parser.add_argument('output_path', help='Path for output text file or directory')
    
    args = parser.parse_args()
    
    # Check if input path is a file or directory
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    
    if input_path.is_file():
        # Process single file
        if not input_path.suffix.lower() == '.pdf':
            logger.error("Input file must be a PDF")
            return
        
        # If output path is a directory, create filename
        if output_path.is_dir():
            output_path = output_path / f"{input_path.stem}.txt"
            
        convert_pdf_to_text(str(input_path), str(output_path))
    
    elif input_path.is_dir():
        # Process directory
        process_directory(str(input_path), str(output_path))
    
    else:
        logger.error("Input path does not exist")
        return

if __name__ == "__main__":
    main()