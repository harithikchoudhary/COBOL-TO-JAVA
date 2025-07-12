#!/usr/bin/env python3
"""
Test script for enhanced COBOL to .NET 8 conversion functionality.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from routes.conversion import analyze_cobol_structure, build_enhanced_conversion_instructions, validate_generated_components

def test_cobol_analysis():
    """Test the COBOL structure analysis functionality."""
    
    # Sample COBOL code with multiple programs and operations
    sample_cobol = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CUSTOMER-PROGRAM.
       AUTHOR. TEST AUTHOR.
       DATE-WRITTEN. 2024-01-01.
       
       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  CUSTOMER-RECORD.
           05  CUSTOMER-ID    PIC X(10).
           05  CUSTOMER-NAME  PIC X(50).
           05  CUSTOMER-ADDR  PIC X(100).
       
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           OPEN INPUT CUSTOMER-FILE
           READ CUSTOMER-FILE
           PERFORM PROCESS-CUSTOMER
           CLOSE CUSTOMER-FILE
           STOP RUN.
       
       PROCESS-CUSTOMER.
           DISPLAY "Processing customer: " CUSTOMER-NAME
           EXEC SQL
               SELECT * FROM CUSTOMERS WHERE ID = :CUSTOMER-ID
           END-EXEC.
       
       IDENTIFICATION DIVISION.
       PROGRAM-ID. ORDER-PROGRAM.
       
       ENVIRONMENT DIVISION.
       
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  ORDER-RECORD.
           05  ORDER-ID       PIC X(10).
           05  ORDER-DATE     PIC X(8).
           05  ORDER-AMOUNT   PIC 9(10)V99.
       
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           OPEN INPUT ORDER-FILE
           READ ORDER-FILE
           PERFORM PROCESS-ORDER
           CLOSE ORDER-FILE
           STOP RUN.
       
       PROCESS-ORDER.
           DISPLAY "Processing order: " ORDER-ID
           EXEC SQL
               INSERT INTO ORDERS (ID, DATE, AMOUNT) 
               VALUES (:ORDER-ID, :ORDER-DATE, :ORDER-AMOUNT)
           END-EXEC.
    """
    
    print("Testing COBOL structure analysis...")
    analysis = analyze_cobol_structure(sample_cobol)
    
    print(f"Analysis Results:")
    print(f"- Programs found: {len(analysis['programs'])}")
    print(f"- Sections found: {len(analysis['sections'])}")
    print(f"- Paragraphs found: {len(analysis['paragraphs'])}")
    print(f"- File operations: {len(analysis['file_operations'])}")
    print(f"- Database operations: {len(analysis['database_operations'])}")
    print(f"- Recommended components: {analysis['recommended_components']}")
    
    # Test enhanced instructions
    instructions = build_enhanced_conversion_instructions(analysis)
    print(f"\nEnhanced Instructions Length: {len(instructions)} characters")
    
    # Test validation with sample converted code
    sample_converted_code = {
        "Controller": {"FileName": "CustomerController.cs", "Path": "Controllers/", "content": "public class CustomerController { }"},
        "Controller2": {"FileName": "OrderController.cs", "Path": "Controllers/", "content": "public class OrderController { }"},
        "Service": {"FileName": "CustomerService.cs", "Path": "Services/Interfaces/", "content": "public interface ICustomerService { }"},
        "ServiceImpl": {"FileName": "CustomerServiceImpl.cs", "Path": "Services/", "content": "public class CustomerServiceImpl { }"},
        "Entity": {"FileName": "Customer.cs", "Path": "Models/", "content": "public class Customer { }"},
        "Entity2": {"FileName": "Order.cs", "Path": "Models/", "content": "public class Order { }"},
        "Repository": {"FileName": "CustomerRepository.cs", "Path": "Repositories/Interfaces/", "content": "public interface ICustomerRepository { }"},
        "RepositoryImpl": {"FileName": "CustomerRepositoryImpl.cs", "Path": "Repositories/", "content": "public class CustomerRepositoryImpl { }"}
    }
    
    validation = validate_generated_components(sample_converted_code, analysis)
    print(f"\nValidation Results:")
    print(f"- Is valid: {validation['is_valid']}")
    print(f"- Component counts: {validation['component_counts']}")
    if validation['issues']:
        print(f"- Issues: {validation['issues']}")
    if validation['recommendations']:
        print(f"- Recommendations: {validation['recommendations']}")
    
    print("\n✅ Enhanced conversion functionality test completed successfully!")

if __name__ == "__main__":
    test_cobol_analysis() 