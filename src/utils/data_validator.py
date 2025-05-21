"""
Data validation module for ensuring data quality before insertion into vector database.

This module provides functions to validate structured data extracted from boAt website.
"""

import json
from typing import Dict, List, Tuple, Any, Optional

def validate_structured_content(data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate the quality of structured content extracted by Gemini.
    
    Args:
        data: Dictionary containing structured content
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check for error key - indicates Gemini processing failed
    if data.get('error'):
        issues.append(f"Processing error: {data.get('error')}")
        return False, issues
        
    # If it's return policy data
    if 'replacement_timeframe' in data:
        # Check replacement timeframe
        if data.get('replacement_timeframe') is None:
            issues.append("Missing replacement timeframe")
        
        # Check conditions lists
        if not data.get('replacement_conditions'):
            issues.append("Missing replacement conditions")
        elif not isinstance(data.get('replacement_conditions'), list):
            issues.append("replacement_conditions should be a list")
            
        if not data.get('non_replacement_conditions'):
            issues.append("Missing non-replacement conditions")
        elif not isinstance(data.get('non_replacement_conditions'), list):
            issues.append("non_replacement_conditions should be a list")
            
        if not data.get('cancellation_conditions'):
            issues.append("Missing cancellation conditions")
        elif not isinstance(data.get('cancellation_conditions'), list):
            issues.append("cancellation_conditions should be a list")
            
        if not data.get('return_policy_summary'):
            issues.append("Missing return policy summary")
    
    # If it's service center data
    elif 'states_with_centers' in data:
        # Check states list
        if not data.get('states_with_centers'):
            issues.append("Missing states with service centers")
        elif not isinstance(data.get('states_with_centers'), list):
            issues.append("states_with_centers should be a list")
        elif len(data.get('states_with_centers', [])) < 5:
            issues.append("Too few states listed (expected at least 5)")
            
        # Check for holiday info
        if not data.get('holiday_info'):
            issues.append("Missing holiday information")
            
        # Check for contact details
        if not data.get('contact_details'):
            issues.append("Missing contact details")
    
    else:
        issues.append("Unknown data structure - neither return policy nor service center data detected")
    
    return len(issues) == 0, issues

def validate_vector_document(doc: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a document prepared for vector database.
    
    Args:
        doc: Document to validate
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check required fields
    if not doc.get('id'):
        issues.append("Missing document ID")
        
    if not doc.get('text'):
        issues.append("Missing document text")
    elif len(doc.get('text', '')) < 100:
        issues.append(f"Document text too short: {len(doc.get('text', ''))} chars (min 100)")
        
    # Check metadata
    if not doc.get('metadata'):
        issues.append("Missing metadata")
    else:
        metadata = doc.get('metadata', {})
        if not metadata.get('category'):
            issues.append("Missing category in metadata")
        if not metadata.get('source_url'):
            issues.append("Missing source URL in metadata")
    
    return len(issues) == 0, issues

def validate_processed_data_file(file_path: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a processed data file and return validation report.
    
    Args:
        file_path: Path to the processed data JSON file
        
    Returns:
        Tuple of (is_valid, validation_report)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return False, {"error": f"Failed to read file: {str(e)}"}
    
    all_valid = True
    report = {
        "total_items": len(data),
        "valid_items": 0,
        "issues_by_item": {},
        "overall_issues": []
    }
    
    for i, item in enumerate(data):
        # Basic structure check
        if not isinstance(item, dict):
            report["overall_issues"].append(f"Item {i} is not a dictionary")
            all_valid = False
            continue
            
        if not all(k in item for k in ['url', 'category', 'raw_content', 'structured_content']):
            report["overall_issues"].append(f"Item {i} missing required fields")
            all_valid = False
            continue
            
        # Validate structured content
        is_valid, issues = validate_structured_content(item.get('structured_content', {}))
        if not is_valid:
            all_valid = False
            report["issues_by_item"][i] = issues
        else:
            report["valid_items"] += 1
    
    report["all_valid"] = all_valid
    return all_valid, report

def validate_vector_docs_file(file_path: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a vector documents file and return validation report.
    
    Args:
        file_path: Path to the vector documents JSON file
        
    Returns:
        Tuple of (is_valid, validation_report)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            docs = json.load(f)
    except Exception as e:
        return False, {"error": f"Failed to read file: {str(e)}"}
    
    all_valid = True
    report = {
        "total_docs": len(docs),
        "valid_docs": 0,
        "issues_by_doc": {},
        "overall_issues": []
    }
    
    # Check for duplicate IDs
    ids = [doc.get('id') for doc in docs if 'id' in doc]
    duplicate_ids = set([id for id in ids if ids.count(id) > 1])
    if duplicate_ids:
        report["overall_issues"].append(f"Duplicate document IDs found: {duplicate_ids}")
        all_valid = False
    
    for i, doc in enumerate(docs):
        # Validate each document
        is_valid, issues = validate_vector_document(doc)
        if not is_valid:
            all_valid = False
            report["issues_by_doc"][i] = issues
        else:
            report["valid_docs"] += 1
    
    report["all_valid"] = all_valid
    return all_valid, report

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate data files for the chatbot")
    parser.add_argument("--processed", default="../data/gemini_processed.json", 
                        help="Path to processed data JSON file")
    parser.add_argument("--vector", default="../data/gemini_vector_docs.json",
                        help="Path to vector documents JSON file")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed validation report")
    
    args = parser.parse_args()
    
    # Validate processed data
    print(f"Validating processed data: {args.processed}")
    processed_valid, processed_report = validate_processed_data_file(args.processed)
    
    if processed_valid:
        print(f"✅ Processed data validation passed: {processed_report['valid_items']}/{processed_report['total_items']} items valid")
    else:
        print(f"❌ Processed data validation failed: {processed_report['valid_items']}/{processed_report['total_items']} items valid")
        if args.verbose:
            print("\nIssues:")
            for item_idx, issues in processed_report["issues_by_item"].items():
                print(f"  Item {item_idx}:")
                for issue in issues:
                    print(f"    - {issue}")
            
            if processed_report["overall_issues"]:
                print("\nOverall issues:")
                for issue in processed_report["overall_issues"]:
                    print(f"  - {issue}")
    
    # Validate vector docs
    print(f"\nValidating vector documents: {args.vector}")
    vector_valid, vector_report = validate_vector_docs_file(args.vector)
    
    if vector_valid:
        print(f"✅ Vector documents validation passed: {vector_report['valid_docs']}/{vector_report['total_docs']} documents valid")
    else:
        print(f"❌ Vector documents validation failed: {vector_report['valid_docs']}/{vector_report['total_docs']} documents valid")
        if args.verbose:
            print("\nIssues:")
            for doc_idx, issues in vector_report["issues_by_doc"].items():
                print(f"  Document {doc_idx}:")
                for issue in issues:
                    print(f"    - {issue}")
            
            if vector_report["overall_issues"]:
                print("\nOverall issues:")
                for issue in vector_report["overall_issues"]:
                    print(f"  - {issue}")
    
    # Exit with appropriate code
    if processed_valid and vector_valid:
        print("\n🎉 All validations passed!")
        sys.exit(0)
    else:
        print("\n❌ Some validations failed. Fix issues before proceeding.")
        sys.exit(1) 