import re
from typing import List, Dict, Optional, Tuple, NamedTuple
from dataclasses import dataclass
from datetime import datetime
import csv

@dataclass
class Transaction:
    date: datetime
    channel: str
    details: str
    transaction_type: str
    recipient: str
    amount: float
    balance: float
    full_text: str

def extract_recipient(text: str) -> str:
    """Extract recipient or sender information from text."""
    patterns = [
        (r'จาก\s+([^\s].*?)(?:\+\+|$)', 'จาก'),
        (r'โอนไป\s+([^\s].*?)(?:\+\+|$)', 'โอนไป'),
        (r'รหัสอ้างอิง\s+([^\s]+)', 'รหัสอ้างอิง'),
        (r'เพื่อชำระ\s+([^\s].*?)(?:\+\+|$)', 'เพื่อชำระ')
    ]
    
    for pattern, keyword in patterns:
        if keyword in text:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
    return ''

def determine_transaction_type(text: str) -> Tuple[str, bool]:
    """Determine transaction type and whether it's outbound."""
    outbound_keywords = ['โอนเงิน', 'ชำระเงิน', 'ค่าธรรมเนียม', 'หักบัญชี']
    inbound_keywords = ['รับโอนเงิน', 'รับโอนเงินผ่าน QR']
    
    # First check for inbound keywords
    for keyword in inbound_keywords:
        if keyword in text:
            return keyword, False
            
    # Then check for outbound keywords
    for keyword in outbound_keywords:
        if keyword in text:
            return keyword, True
            
    # Default to inbound if no keywords found
    return '', False

def clean_text_sections(text: str) -> str:
    """Pre-process text to handle wrapped lines and clean up formatting."""
    sections = text.split('KBPDF (FM001-V.6) 01/1A2-0 (05-19)')
    cleaned_sections = []
    
    for section in sections:
        if 'ยอดยกมา' not in section:
            continue
            
        lines = section.split('\n')
        cleaned_lines = []
        current_line = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            date_match = re.match(r'^\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}', line)
            
            if date_match:
                if current_line:
                    cleaned_lines.append(current_line)
                current_line = line
            else:
                current_line = f"{current_line} {line}"
        
        if current_line:
            cleaned_lines.append(current_line)
            
        cleaned_sections.append('\n'.join(cleaned_lines))
    
    return '\n'.join(cleaned_sections)

def extract_amount(text: str) -> Optional[float]:
    """Extract amount from text, handling Thai number format."""
    try:
        return float(text.replace(',', ''))
    except ValueError:
        return None

def find_last_two_numbers(text: str) -> Tuple[List[float], str]:
    """Find the last two numbers (balance and amount) in text."""
    words = text.split()
    numbers = []
    non_amount_text = []
    
    for i in range(len(words) - 1, -1, -1):
        word = words[i]
        if len(numbers) < 2 and re.match(r'^\d+(?:,\d{3})*(?:\.\d{2})?$', word):
            numbers.insert(0, extract_amount(word))
        else:
            non_amount_text.insert(0, word)
    
    return numbers, ' '.join(non_amount_text)

def parse_transaction_line(line: str) -> Optional[Transaction]:
    """Parse a single transaction line."""
    date_match = re.match(r'^(\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2})', line)
    if not date_match:
        return None
        
    try:
        datetime_str = date_match.group(1)
        date = datetime.strptime(datetime_str, "%d-%m-%y %H:%M")
        
        remaining_text = line[len(datetime_str):].strip()
        numbers, content = find_last_two_numbers(remaining_text)
        
        if len(numbers) < 2:
            return None
            
        balance = numbers[-2]
        amount = numbers[-1]
        
        # Split content into channel and details
        parts = content.split(maxsplit=1)
        channel = parts[0]
        details = parts[1] if len(parts) > 1 else ""
        
        # Clean up channel names
        if channel == "K" and details.startswith("PLUS"):
            channel = "K PLUS"
            details = details[5:].strip()
        elif channel == "EDC/K" and details.startswith("SHOP"):
            channel = "EDC/K SHOP"
            details = details[5:].strip()
        elif channel == "MAKE" and details.startswith("by"):
            channel = "MAKE by KBank"
            details = details[8:].strip()
        
        # Extract transaction type and determine if outbound
        transaction_type, is_outbound = determine_transaction_type(details)
        
        # Extract recipient/sender information
        recipient = extract_recipient(details)
        
        # Adjust amount sign based on transaction direction
        if is_outbound:
            amount = -abs(amount)
        
        return Transaction(
            date=date,
            channel=channel,
            details=details,
            transaction_type=transaction_type,
            recipient=recipient,
            amount=amount,
            balance=balance,
            full_text=line.strip()
        )
    
    except Exception as e:
        print(f"Error parsing line: {line}")
        print(f"Error: {str(e)}")
        return None

def parse_bank_statement(text: str) -> List[Transaction]:
    """Parse the entire bank statement text."""
    cleaned_text = clean_text_sections(text)
    
    transactions = []
    for line in cleaned_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        transaction = parse_transaction_line(line)
        if transaction:
            transactions.append(transaction)
    
    return transactions

def save_to_csv(transactions: List[Transaction], output_file: str):
    """Save transactions to CSV file."""
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow([
            'Date', 'Time', 'Channel', 'Details', 
            'Transaction Type', 'Recipient', 'Amount', 'Balance'
        ])
        
        # Write transactions
        for t in transactions:
            writer.writerow([
                t.date.strftime("%d-%m-%y"),
                t.date.strftime("%H:%M"),
                t.channel,
                t.details,
                t.transaction_type,
                t.recipient,
                f"{t.amount:.2f}",
                f"{t.balance:.2f}"
            ])

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python parser.py <input_file>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        transactions = parse_bank_statement(text)
        
        # Save to CSV
        output_file = 'transactions.csv'
        save_to_csv(transactions, output_file)
        
        print(f"Successfully parsed {len(transactions)} transactions.")
        print(f"Output written to {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)