#!/usr/bin/env python3
"""
Service center scraper using Playwright.
This scraper is specialized for handling the dynamic accordion-style content
on boAt's service center page.
"""
import os
import json
import asyncio
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from playwright.async_api import async_playwright, TimeoutError
except ImportError:
    print("Playwright not found. Installing...")
    import subprocess
    subprocess.check_call(["pip", "install", "playwright"])
    from playwright.async_api import async_playwright, TimeoutError
    
    # Install browsers
    print("Installing Playwright browsers...")
    subprocess.check_call(["playwright", "install", "--with-deps", "chromium"])

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def scrape_service_centers(url: str) -> Dict[str, Any]:
    """
    Scrape service center information from the given URL using Playwright.
    
    Args:
        url: The URL of the service center page
        
    Returns:
        Dictionary containing the scraped data
    """
    service_centers = []
    raw_content = ""
    
    logger.info(f"Starting Playwright to scrape {url}")
    async with async_playwright() as p:
        # Launch the browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Navigate to the URL
            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for the page to load fully - use a more general selector
            logger.info("Waiting for page to load...")
            await page.wait_for_selector("body", timeout=15000)
            
            # Wait extra time for JavaScript to execute
            await page.wait_for_timeout(3000)
            
            # Extract the raw text content
            raw_content = await page.evaluate("() => document.body.innerText")
            
            # Take a screenshot for debugging
            logger.info("Taking a screenshot for debugging...")
            debug_dir = Path(__file__).resolve().parent.parent.parent / "data" / "debug"
            debug_dir.mkdir(exist_ok=True, parents=True)
            await page.screenshot(path=str(debug_dir / "service_center_page.png"), full_page=True)
            
            # Different websites might have different ways to structure accordions
            # Try various common selectors for the accordion buttons
            selectors = [
                "button.accordion", 
                ".accordion", 
                "button.accordion-button",
                ".accordion-header button",
                ".accordion-toggle",
                ".collapsible",
                "h2.accordion-header",
                "button[aria-expanded]",
                "h3.section-header",
                "[data-accordion-trigger]"
            ]
            
            accordion_buttons = []
            used_selector = None
            
            for selector in selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    buttons = await page.query_selector_all(selector)
                    if buttons and len(buttons) > 0:
                        accordion_buttons = buttons
                        used_selector = selector
                        logger.info(f"Found {len(buttons)} buttons with selector: {selector}")
                        break
                except Exception as e:
                    logger.error(f"Error with selector {selector}: {e}")
            
            if not accordion_buttons:
                # If no accordion buttons found, try to extract based on HTML structure
                logger.info("No accordion buttons found, trying to extract states from HTML structure")
                
                # Get all heading elements that might contain state names
                headings = await page.query_selector_all("h2, h3, h4")
                
                for heading in headings:
                    heading_text = await heading.inner_text()
                    heading_text = heading_text.strip()
                    
                    if heading_text.upper() == heading_text or heading_text.isupper():  # State names are often in uppercase
                        logger.info(f"Found potential state heading: {heading_text}")
                        
                        service_center_entries = []
                        # Try to find service center entries in divs or paragraphs following this heading
                        next_elements = []
                        
                        # Get the next sibling elements until we hit another heading
                        element = heading
                        while True:
                            element = await page.evaluate("""
                                (element) => {
                                    const nextSibling = element.nextElementSibling;
                                    if (!nextSibling) return null;
                                    return nextSibling;
                                }
                            """, element)
                            
                            if not element:
                                break
                                
                            element_tag = await page.evaluate("(element) => element.tagName.toLowerCase()", element)
                            
                            if element_tag in ["h2", "h3", "h4"]:
                                break
                                
                            next_elements.append(element)
                        
                        # Process the elements we found
                        locations = []
                        for elem in next_elements:
                            elem_text = await elem.inner_text()
                            elem_text = elem_text.strip()
                            
                            if not elem_text:
                                continue
                                
                            # Look for patterns that might indicate a service center entry
                            lines = elem_text.split("\n")
                            
                            if len(lines) >= 2:  # At least a name and some contact info
                                name = lines[0].strip()
                                address = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
                                contact = lines[-1].strip()
                                
                                locations.append({
                                    "name": name,
                                    "address": address,
                                    "contact": contact
                                })
                        
                        if locations:
                            service_centers.append({
                                "state": heading_text,
                                "locations": locations
                            })
                
                if service_centers:
                    logger.info(f"Extracted {len(service_centers)} states using heading-based extraction")
                else:
                    logger.warning("Could not extract any service centers using heading-based approach")
            else:
                # Process each state with the found accordion buttons
                logger.info(f"Processing {len(accordion_buttons)} accordion buttons")
                for i, button in enumerate(accordion_buttons):
                    try:
                        # Get state name
                        state_name = await button.inner_text()
                        state_name = state_name.strip()
                        logger.info(f"Processing state: {state_name}")
                        
                        # Click to expand
                        await button.click()
                        await page.wait_for_timeout(1000)  # Wait longer for animation
                        
                        # After clicking, take a screenshot for debugging
                        await page.screenshot(path=str(debug_dir / f"state_{i}_{state_name}.png"), full_page=False)
                        
                        # Find the service center entries
                        # The structure might vary based on the website design
                        panel_selectors = [
                            f"#{state_name.lower().replace(' ', '-')}",
                            f"div.panel:nth-child({i*2+2})",
                            f"div[aria-labelledby='{state_name.replace(' ', '-')}']",
                            f"div.accordion-content:nth-child({i+1})",
                            "div.panel.show",
                            ".accordion-collapse.show",
                            ".panel-collapse.in"
                        ]
                        
                        # Try to find the panel using various selectors
                        panel = None
                        for selector in panel_selectors:
                            try:
                                panel_elements = await page.query_selector_all(selector)
                                if panel_elements and len(panel_elements) > 0:
                                    for potential_panel in panel_elements:
                                        is_visible = await potential_panel.is_visible()
                                        if is_visible:
                                            panel = potential_panel
                                            logger.info(f"Found visible panel with selector: {selector}")
                                            break
                                if panel:
                                    break
                            except Exception as e:
                                logger.error(f"Error with panel selector {selector}: {e}")
                        
                        if not panel:
                            # Try to get next element sibling which might be the panel
                            panel = await page.evaluate("""
                                (button) => {
                                    const nextSibling = button.nextElementSibling;
                                    if (!nextSibling) return null;
                                    return nextSibling;
                                }
                            """, button)
                            
                        locations = []
                        
                        if panel:
                            # Check if panel is a JSHandle or ElementHandle rather than a string
                            try:
                                # If we can call a method on the panel, it's an element
                                await panel.query_selector("*")
                                is_element = True
                            except Exception:
                                is_element = False
                            
                            if not is_element:
                                logger.warning(f"Panel for {state_name} is not an element, but a string: {panel}")
                                
                                # Try to find the panel by querying the page directly
                                try:
                                    # Try a few common patterns for panel IDs
                                    panel_id = state_name.lower().replace(' ', '-').replace('&', 'and')
                                    direct_panel = await page.query_selector(f"#{panel_id}, .{panel_id}")
                                    if direct_panel:
                                        panel = direct_panel
                                        logger.info(f"Found panel by direct ID/class query: {panel_id}")
                                    else:
                                        # If we couldn't find by ID, try finding by position relative to the button
                                        button_box = await button.bounding_box()
                                        if button_box:
                                            # Look for elements below the button
                                            elements_below = await page.evaluate("""
                                                (y) => {
                                                    const elements = [];
                                                    document.querySelectorAll('div, section, p').forEach(el => {
                                                        const rect = el.getBoundingClientRect();
                                                        if (rect.top > y && rect.width > 100) {
                                                            elements.push({
                                                                element: el,
                                                                distance: rect.top - y
                                                            });
                                                        }
                                                    });
                                                    // Sort by distance
                                                    elements.sort((a, b) => a.distance - b.distance);
                                                    return elements.slice(0, 3).map(e => e.element);
                                                }
                                            """, button_box['y'] + button_box['height'])
                                            
                                            if elements_below and len(elements_below) > 0:
                                                panel = elements_below[0]
                                                logger.info(f"Found panel by position below button")
                                except Exception as panel_find_error:
                                    logger.error(f"Error finding panel for {state_name}: {panel_find_error}")
                                    panel = None
                            
                            # Try to find service center entries within the panel
                            if panel and not isinstance(panel, str):
                                entry_selectors = [
                                    "div.service-center-entry", 
                                    "div.location", 
                                    "div.service-center", 
                                    "address", 
                                    "p", 
                                    "div.container"
                                ]
                                
                                service_center_elements = []
                                for selector in entry_selectors:
                                    try:
                                        elements = await panel.query_selector_all(selector)
                                        if elements and len(elements) > 0:
                                            service_center_elements = elements
                                            logger.info(f"Found {len(elements)} service center entries with selector: {selector}")
                                            break
                                    except Exception as e:
                                        logger.error(f"Error with entry selector {selector}: {e}")
                            
                                # Process each service center entry
                                for center_elem in service_center_elements:
                                    center_text = await center_elem.inner_text()
                                    center_text = center_text.strip()
                                    
                                    if not center_text:
                                        continue
                                    
                                    # Parse the text to extract name, address, and contact info
                                    lines = center_text.split("\n")
                                    
                                    if len(lines) >= 1:
                                        # The entire text is likely the full service center entry
                                        # Treat it as a single entity rather than trying to split it
                                        full_text = center_text
                                        
                                        # Extract pincode if present (common format in Indian addresses)
                                        pincode = None
                                        pincode_match = re.search(r'\s(\d{6})(?:\s|$)', full_text)
                                        if pincode_match:
                                            pincode = pincode_match.group(1)
                                        
                                        # In most entries, the name is at the beginning
                                        # The contact is often at the end (phone numbers)
                                        # The middle part is the address
                                        
                                        # Try to identify if there's a clear shop/office name at the start
                                        name_parts = []
                                        remaining_text = full_text
                                        
                                        # Common prefixes that indicate a business name
                                        name_indicators = [
                                            "LOTUS", "F1", "Mayday", "boAt Exclusive", 
                                            "BT-", "RV", "SIMPLEX", "TELECONNECT",
                                            "TECH", "VIRTUAL", "WINTEL", "MOBILE"
                                        ]
                                        
                                        # Look for a business name indicator
                                        first_line = lines[0].strip() if lines else ""
                                        found_name = False
                                        
                                        if any(indicator in full_text[:100] for indicator in name_indicators):
                                            # If we found a name indicator, use everything up to the first comma or similar
                                            # as the name, or the first line if it's short
                                            if len(first_line) < 100 and "," in first_line:
                                                name = first_line.split(",")[0].strip()
                                                found_name = True
                                            elif len(first_line) < 60:
                                                name = first_line
                                                found_name = True
                                        
                                        if not found_name:
                                            # Try to find a logical split based on patterns in the text
                                            if len(first_line) > 60 and "," in full_text:
                                                # Try to split at the first comma - common pattern is "Name, Address"
                                                first_comma = full_text.find(",")
                                                if first_comma > 10 and first_comma < 100:
                                                    name = full_text[:first_comma].strip()
                                                    address = full_text[first_comma+1:].strip()
                                                    found_name = True
                                                else:
                                                    # If comma is too early or too late, try a different approach
                                                    name = full_text
                                                    address = ""
                                            else:
                                                name = full_text
                                                address = ""
                                            contact = ""
                                        else:
                                            # Try to extract address and contact from remaining text
                                            remaining_lines = lines[1:] if len(lines) > 1 else []
                                            address_parts = []
                                            contact_parts = []
                                            
                                            # Check for phone numbers in the text
                                            phone_matches = re.findall(r'(?<!\d)(\d{10}|\d{3}[-\.\s]\d{3}[-\.\s]\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]\d{4})(?!\d)', full_text)
                                            
                                            # Use more flexible patterns for phone number extraction
                                            phone_patterns = [
                                                r'(?<!\d)(\d{10})(?!\d)',  # 10 digits
                                                r'(?<!\d)(\d{3}[-\.\s]\d{3}[-\.\s]\d{4})(?!\d)',  # 3-3-4 format with separators
                                                r'(?<!\d)(\(\d{3}\)\s*\d{3}[-\.\s]\d{4})(?!\d)',  # (area) code format
                                                r'(?<!\d)(0\d{9,10})(?!\d)',  # 0 followed by 9-10 digits (common in India)
                                                r'(?<!\d)(\+\d{2}[-\.\s]\d{10})(?!\d)',  # +country code format
                                                r'Phone:?\s*(\d[\d\s-]{8,12}\d)',  # Phone: followed by digits with possible spaces
                                                r'Tel:?\s*(\d[\d\s-]{8,12}\d)',  # Tel: followed by digits with possible spaces
                                                r'Contact:?\s*(\d[\d\s-]{8,12}\d)',  # Contact: followed by digits
                                                r'(?<!\d)(\d{5}[-\.\s]\d{5})(?!\d)'  # 5-5 format (common in India)
                                            ]
                                            
                                            all_phone_matches = []
                                            for pattern in phone_patterns:
                                                matches = re.findall(pattern, full_text)
                                                all_phone_matches.extend(matches)
                                            
                                            # Also check if any line has words like "phone", "mobile", "contact", "call", etc.
                                            contact_keywords = ["phone", "mobile", "contact", "call", "tel", "telephone"]
                                            
                                            for line in remaining_lines:
                                                line = line.strip()
                                                if not line:
                                                    continue
                                                
                                                # Check if this line has a phone number
                                                if any(phone in line for phone in all_phone_matches):
                                                    contact_parts.append(line)
                                                # Also check for lines that might contain contact info based on keywords
                                                elif any(keyword in line.lower() for keyword in contact_keywords):
                                                    contact_parts.append(line)
                                                else:
                                                    address_parts.append(line)
                                            
                                            address = ", ".join(address_parts) if address_parts else ""
                                            contact = ", ".join(contact_parts) if contact_parts else ""
                                            
                                            # If we have a pincode but it's not in the address, add it
                                            if pincode and address and pincode not in address:
                                                address += f" - {pincode}"
                                        
                                        # If we have a "name" that looks like a full entry, try to parse it better
                                        if len(name) > 100 and "," in name:
                                            # This is likely a full entry with name, address, and possibly contact
                                            parts = name.split(",")
                                            if len(parts) >= 2:
                                                # Name is usually the first part
                                                name = parts[0].strip()
                                                # Address is the middle parts
                                                address_parts = parts[1:-1] if len(parts) > 2 else [parts[1]]
                                                address = ", ".join(address_parts).strip()
                                                # Contact might be the last part if it looks like a phone number
                                                last_part = parts[-1].strip()
                                                if re.search(r'\d{10}|\d{3}[-\.\s]\d{3}[-\.\s]\d{4}', last_part):
                                                    contact = last_part
                                                else:
                                                    # If no phone number, treat last part as address too
                                                    address = (address + ", " + last_part).strip()
                                        
                                        # Special case: If name contains the full address including pincode at the end
                                        # Extract the pincode and use it to split the name into name+address
                                        if not address and len(name) > 60:
                                            pincode_match = re.search(r'(\d{6})(?:\s|$)', name)
                                            if pincode_match:
                                                pincode_pos = pincode_match.start()
                                                # Look for a natural break point before the pincode
                                                break_pos = name.rfind(",", 0, pincode_pos)
                                                if break_pos == -1:
                                                    break_pos = name.rfind(" - ", 0, pincode_pos)
                                                
                                                if break_pos > 10:
                                                    # Found a good break point
                                                    shop_name = name[:break_pos].strip()
                                                    addr = name[break_pos:].strip()
                                                    
                                                    # Update the entry
                                                    name = shop_name
                                                    address = addr
                                        
                                        locations.append({
                                            "name": name,
                                            "address": address,
                                            "contact": contact
                                        })
                                        
                                        # Now try to extract contact from service center name field
                                        # Common pattern in boAt service centers is that phone numbers
                                        # often follow the pincode (6 digits) at the end of the entry
                                        pincode_phone_pattern = r'(\d{6})(?:\s+|,\s*)(\d{10}|\d{5}[-\s]\d{5}|\d{3}[-\s]\d{3}[-\s]\d{4})'
                                        pincode_phone_match = re.search(pincode_phone_pattern, name)
                                        
                                        if pincode_phone_match:
                                            phone_number = pincode_phone_match.group(2)
                                            if not locations[-1]["contact"]:
                                                locations[-1]["contact"] = phone_number
                            elif panel and isinstance(panel, str):
                                # If panel is a string, it might be HTML content
                                logger.info(f"Panel for {state_name} is a string, trying to extract locations directly")
                                center_texts = panel.split("<br>")
                                for center_text in center_texts:
                                    if center_text.strip():
                                        # Try to extract structured data from the text
                                        lines = center_text.strip().split("\n")
                                        if len(lines) >= 1:
                                            name = lines[0].strip()
                                            address = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
                                            contact = lines[-1].strip() if len(lines) > 1 else ""
                                            
                                            locations.append({
                                                "name": name,
                                                "address": address,
                                                "contact": contact
                                            })
                        
                        # If no entries found or panel not found, still record the state
                        service_centers.append({
                            "state": state_name,
                            "locations": locations
                        })
                        
                        # If we couldn't find any locations but we have a state name,
                        # try to extract service centers by looking at text around the state name
                        if not locations:
                            logger.info(f"No locations found for {state_name}, trying text-based extraction")
                            try:
                                # Find all text nodes that might contain service center info
                                service_center_text = await page.evaluate("""
                                    (stateName) => {
                                        const stateTexts = [];
                                        const elements = Array.from(document.querySelectorAll('p, div, span, li'));
                                        
                                        // Find elements that contain the state name
                                        const stateElements = elements.filter(el => 
                                            el.innerText && el.innerText.includes(stateName));
                                        
                                        if (stateElements.length > 0) {
                                            // Look at the next few elements after each state element
                                            for (const stateEl of stateElements) {
                                                let currentEl = stateEl;
                                                for (let i = 0; i < 5; i++) {  // Check next 5 siblings
                                                    if (!currentEl.nextElementSibling) break;
                                                    currentEl = currentEl.nextElementSibling;
                                                    
                                                    // Skip elements with very short text
                                                    const text = currentEl.innerText?.trim();
                                                    if (!text || text.length < 10) continue;
                                                    
                                                    // Skip if it looks like another state name
                                                    if (text.toUpperCase() == text || text.length < 20) continue;
                                                    
                                                    stateTexts.push(text);
                                                }
                                            }
                                        }
                                        
                                        return stateTexts;
                                    }
                                """, state_name)
                                
                                # Process the text to extract service center info
                                for text in service_center_text:
                                    # Split by newlines or long spaces
                                    entries = text.split("\n\n")
                                    if len(entries) == 1:
                                        entries = text.split("  ")
                                    
                                    for entry in entries:
                                        entry = entry.strip()
                                        if len(entry) < 15:  # Skip very short entries
                                            continue
                                            
                                        lines = entry.split("\n")
                                        if len(lines) >= 1:
                                            name = lines[0].strip()
                                            address = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
                                            contact = lines[-1].strip() if len(lines) > 1 else ""
                                            
                                            # Add to the locations list for this state
                                            service_centers[-1]["locations"].append({
                                                "name": name,
                                                "address": address,
                                                "contact": contact
                                            })
                                            
                                logger.info(f"Added {len(service_centers[-1]['locations']) - len(locations)} locations through text-based extraction")
                            except Exception as e:
                                logger.error(f"Error in text-based extraction for {state_name}: {e}")
                        
                        # Click to collapse (if needed)
                        await button.click()
                        await page.wait_for_timeout(500)
                        
                    except Exception as e:
                        logger.error(f"Error processing state button {i}: {e}")
                        continue
            
            # If we still have no service centers, try generic extraction from page source
            if not service_centers:
                logger.info("Trying generic extraction from page source")
                
                # Get the page HTML
                html = await page.content()
                
                # Get all text content in structured form
                page_text = await page.evaluate("""
                    () => {
                        const sections = [];
                        const allElements = document.body.querySelectorAll('*');
                        const seen = new Set();
                        
                        for (const el of allElements) {
                            if (seen.has(el)) continue;
                            
                            // Check if this element has sizable text
                            const text = el.innerText?.trim();
                            if (text && text.length > 10) {
                                // Is it a heading-like element?
                                const tagName = el.tagName.toLowerCase();
                                if (tagName.startsWith('h') || el.className.includes('head') || el.className.includes('title')) {
                                    const contentElements = [];
                                    let sibling = el.nextElementSibling;
                                    
                                    while (sibling && !sibling.tagName.toLowerCase().startsWith('h') && 
                                          !sibling.className.includes('head') && !sibling.className.includes('title')) {
                                        const siblingText = sibling.innerText?.trim();
                                        if (siblingText && siblingText.length > 10) {
                                            contentElements.push(sibling);
                                            seen.add(sibling);
                                        }
                                        sibling = sibling.nextElementSibling;
                                    }
                                    
                                    if (contentElements.length > 0) {
                                        sections.push({
                                            heading: text,
                                            content: contentElements.map(el => el.innerText?.trim()).filter(Boolean)
                                        });
                                    }
                                }
                            }
                        }
                        
                        return sections;
                    }
                """)
                
                # Process the sections
                for section in page_text:
                    heading = section.get("heading", "")
                    content = section.get("content", [])
                    
                    if heading and content:
                        # Try to determine if this is a state section
                        if heading.upper() == heading or any(state in heading.upper() for state in [
                            "DELHI", "MUMBAI", "CHENNAI", "KOLKATA", "BANGALORE", 
                            "HYDERABAD", "PUNJAB", "UTTAR PRADESH", "TAMIL NADU"
                        ]):
                            locations = []
                            
                            for item in content:
                                if len(item.split("\n")) >= 2:  # At least name and address
                                    lines = item.split("\n")
                                    name = lines[0].strip()
                                    address = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
                                    contact = lines[-1].strip() if len(lines) > 1 else ""
                                    
                                    locations.append({
                                        "name": name,
                                        "address": address,
                                        "contact": contact
                                    })
                            
                            if locations:
                                service_centers.append({
                                    "state": heading,
                                    "locations": locations
                                })
                
                if service_centers:
                    logger.info(f"Extracted {len(service_centers)} states using generic extraction")
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        finally:
            await browser.close()
    
    return {
        "url": url,
        "category": "service_center",
        "raw_content": raw_content,
        "structured_content": {
            "service_centers": service_centers
        }
    }

async def main():
    """Run the scraper."""
    print("Running Playwright Service Center Scraper")
    print("=" * 50)
    
    url = "https://www.boat-lifestyle.com/pages/service-center-list"
    
    # Scrape the service centers
    scraped_data = await scrape_service_centers(url)
    
    # Clean up the data - remove any "ref: <Node>" values
    if "structured_content" in scraped_data and "service_centers" in scraped_data["structured_content"]:
        for state in scraped_data["structured_content"]["service_centers"]:
            cleaned_locations = []
            for location in state.get("locations", []):
                # Check if this location has "ref: <Node>" as a value
                if location.get("name") == "ref: <Node>":
                    continue
                
                # Ensure address and contact are not None
                location["address"] = location.get("address", "")
                location["contact"] = location.get("contact", "")
                
                # Look for contact information in the name field
                if not location["contact"] and re.search(r'\d{10}|\d{5}[-\s]\d{5}', location["name"]):
                    # Extract any 10-digit number or 5-5 format number
                    phone_match = re.search(r'(\d{10}|\d{5}[-\s]\d{5})', location["name"])
                    if phone_match:
                        location["contact"] = phone_match.group(0)
                
                # Try to extract phone numbers that appear after pincodes
                # Format: <pincode> <phone>
                if not location["contact"]:
                    pincode_phone_pattern = r'(\d{6})(?:\s+|,\s*)(\d{10}|\d{5}[-\s]\d{5})'
                    
                    # Look in both name and address
                    for field in ["name", "address"]:
                        if not location["contact"] and location[field]:
                            pincode_phone_match = re.search(pincode_phone_pattern, location[field])
                            if pincode_phone_match:
                                location["contact"] = pincode_phone_match.group(2)
                                
                                # Remove the phone number from the field
                                cleaned_text = location[field].replace(pincode_phone_match.group(2), "").strip()
                                # Remove any double spaces created
                                cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
                                location[field] = cleaned_text
                
                # Also search for Ph: or Phone: patterns
                if not location["contact"]:
                    for field in ["name", "address"]:
                        if location[field]:
                            phone_label_match = re.search(r'(?:Ph|Phone|Tel|Mobile)[:.\s]+(\d[\d\s-]{8,12}\d)', location[field], re.IGNORECASE)
                            if phone_label_match:
                                location["contact"] = phone_label_match.group(1)
                                
                                # Remove the labeled phone from the field
                                cleaned_text = re.sub(r'(?:Ph|Phone|Tel|Mobile)[:.\s]+\d[\d\s-]{8,12}\d', '', location[field], flags=re.IGNORECASE).strip()
                                location[field] = cleaned_text
                
                # Clean up pincode from the end of the name if it's repeated in address
                if location["address"]:
                    pincode_match = re.search(r'\s(\d{6})(?:\s|$)', location["name"])
                    if pincode_match and pincode_match.group(1) in location["address"]:
                        location["name"] = re.sub(r'\s\d{6}(?:\s|$)', '', location["name"]).strip()
                
                # Cleanup common service center name patterns to make them more readable
                location["name"] = location["name"].replace(", ", ",\n")
                
                # Format long names more readably by adding line breaks
                if len(location["name"]) > 60 and "," in location["name"]:
                    parts = location["name"].split(",")
                    location["name"] = parts[0].strip()
                    if not location["address"]:
                        location["address"] = ", ".join(parts[1:]).strip()
                
                cleaned_locations.append(location)
            
            # Update the locations array
            state["locations"] = cleaned_locations
        
        # Find states with no locations and try to extract them from the raw content
        empty_states = [state for state in scraped_data["structured_content"]["service_centers"] if not state.get("locations")]
        if empty_states:
            logger.info(f"Found {len(empty_states)} states with no locations. Trying text-based extraction from raw content.")
            raw_content = scraped_data.get("raw_content", "")
            
            for empty_state in empty_states:
                state_name = empty_state.get("state", "")
                if not state_name or not raw_content:
                    continue
                
                logger.info(f"Attempting to extract service centers for {state_name} from raw content")
                
                # Find sections of text that might contain this state's service centers
                # First, find where the state name appears in the raw content
                state_positions = []
                start_pos = 0
                while True:
                    pos = raw_content.find(state_name, start_pos)
                    if pos == -1:
                        break
                    state_positions.append(pos)
                    start_pos = pos + 1
                
                # For each occurrence, try to extract service center info
                potential_centers = []
                for pos in state_positions:
                    # Look for text after the state name, stopping at the next state name or section
                    # Find the end of this section
                    next_section_start = len(raw_content)
                    
                    # Look for the next state name or common section divider
                    for other_state in scraped_data["structured_content"]["service_centers"]:
                        other_name = other_state.get("state", "")
                        if other_name and other_name != state_name:
                            other_pos = raw_content.find(other_name, pos + len(state_name))
                            if other_pos != -1 and other_pos < next_section_start:
                                next_section_start = other_pos
                    
                    # Also check for common section dividers
                    for divider in ["Subscribe", "Help", "Shop", "Company", "Let's get social"]:
                        div_pos = raw_content.find(divider, pos + len(state_name))
                        if div_pos != -1 and div_pos < next_section_start:
                            next_section_start = div_pos
                    
                    # Extract the section text
                    section_text = raw_content[pos + len(state_name):next_section_start].strip()
                    
                    # Split the section text into potential service center entries
                    # Service center entries often contain specific keywords or patterns
                    center_indicators = ["Floor", "Shop No", "Shop no", "Office", "Building", "Plaza", "Complex", "Road"]
                    
                    # Look for these indicators in the section text
                    for indicator in center_indicators:
                        indicator_pos = section_text.find(indicator)
                        if indicator_pos != -1:
                            # Found a potential service center entry
                            # Extract a reasonable amount of text around it
                            start = max(0, indicator_pos - 100)
                            end = min(len(section_text), indicator_pos + 200)
                            
                            # Find natural breakpoints around this position
                            better_start = section_text.rfind("\n\n", 0, indicator_pos)
                            if better_start != -1 and better_start > start - 50:
                                start = better_start + 2  # Skip the newlines
                            
                            better_end = section_text.find("\n\n", indicator_pos)
                            if better_end != -1 and better_end < end + 50:
                                end = better_end
                            
                            center_text = section_text[start:end].strip()
                            
                            # Skip very short entries
                            if len(center_text) < 20:
                                continue
                            
                            # Skip entries that are likely navigation menus or other non-service center text
                            if any(nav in center_text for nav in ["Menu", "Search", "Cart", "Login"]):
                                continue
                            
                            # Make sure it has a pincode or looks like an address
                            if re.search(r'\d{6}', center_text) or any(addr in center_text for addr in ["Road", "Street", "Avenue", "Lane"]):
                                potential_centers.append(center_text)
                
                # Process the potential centers to create structured entries
                for center_text in potential_centers:
                    # Skip entries that are too short to be meaningful
                    if len(center_text) < 40:
                        continue
                        
                    # Try to parse name, address, and contact
                    lines = center_text.split("\n")
                    
                    if len(lines) >= 1:
                        # Default is to use first line as name and rest as address
                        name = lines[0].strip()
                        address = "\n".join(lines[1:]).strip()
                        contact = ""
                        
                        # Look for phone numbers
                        phone_match = re.search(r'(?<!\d)(\d{10}|\d{3}[-\.\s]\d{3}[-\.\s]\d{4})(?!\d)', center_text)
                        if phone_match:
                            contact = phone_match.group(0)
                            
                            # Remove the phone number from the address if it's there
                            address = address.replace(contact, "").strip()
                        
                        # If the "name" is too long, it might be both name and address
                        if len(name) > 60 and "," in name:
                            parts = name.split(",", 1)
                            name = parts[0].strip()
                            if address:
                                address = parts[1].strip() + ", " + address
                            else:
                                address = parts[1].strip()
                        
                        # Look for contact info in the address
                        phone_patterns = [
                            r'(?<!\d)(\d{10})(?!\d)',  # 10 digits
                            r'(?<!\d)(\d{3}[-\.\s]\d{3}[-\.\s]\d{4})(?!\d)',  # 3-3-4 format with separators
                            r'(?<!\d)(\(\d{3}\)\s*\d{3}[-\.\s]\d{4})(?!\d)',  # (area) code format
                            r'(?<!\d)(0\d{9,10})(?!\d)',  # 0 followed by 9-10 digits (common in India)
                            r'(?<!\d)(\+\d{2}[-\.\s]\d{10})(?!\d)',  # +country code format
                            r'Phone:?\s*(\d[\d\s-]{8,12}\d)',  # Phone: followed by digits with possible spaces
                            r'Tel:?\s*(\d[\d\s-]{8,12}\d)',  # Tel: followed by digits with possible spaces
                            r'Contact:?\s*(\d[\d\s-]{8,12}\d)',  # Contact: followed by digits
                            r'(?<!\d)(\d{5}[-\.\s]\d{5})(?!\d)'  # 5-5 format (common in India)
                        ]
                        
                        contact_numbers = []
                        for pattern in phone_patterns:
                            matches = re.findall(pattern, address)
                            if matches:
                                for match in matches:
                                    contact_numbers.append(match)
                                    address = address.replace(match, "").strip()
                                    # Clean up any leftover text like "Phone:", "Tel:"
                                    for prefix in ["Phone:", "Phone", "Tel:", "Tel", "Contact:", "Contact"]:
                                        address = address.replace(prefix, "").strip()
                                    # Clean up any punctuation left at the beginning or end
                                    address = address.strip(".,;: ")
                        
                        if contact_numbers:
                            if contact:
                                contact += ", " + ", ".join(contact_numbers)
                            else:
                                contact = ", ".join(contact_numbers)
                        
                        # Add this location to the state
                        empty_state["locations"].append({
                            "name": name,
                            "address": address,
                            "contact": contact
                        })
                
                logger.info(f"Added {len(empty_state['locations'])} locations for {state_name} from raw content")
    
    # Get the project root directory
    project_root = Path(__file__).resolve().parent.parent.parent
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # Save the scraped data
    output_file = os.path.join(data_dir, "playwright_service_centers.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, indent=2)
    
    print(f"Saved scraped data to {output_file}")
    
    # Print summary
    if "structured_content" in scraped_data and "service_centers" in scraped_data["structured_content"]:
        service_centers = scraped_data["structured_content"]["service_centers"]
        print(f"\nFound {len(service_centers)} states/regions")
        
        total_locations = sum(len(state.get("locations", [])) for state in service_centers)
        print(f"Total service center locations: {total_locations}")
        
        # Count states with no locations
        empty_states = sum(1 for state in service_centers if not state.get("locations"))
        print(f"States with no locations: {empty_states}")
        
        # Print some sample data
        if service_centers:
            for state in service_centers:
                if state.get("locations"):
                    print(f"\nSample data for state: {state['state']}")
                    print(f"Number of locations: {len(state.get('locations', []))}")
                    
                    if state.get("locations"):
                        print("\nFirst location details:")
                        location = state["locations"][0]
                        print(f"Name: {location.get('name', 'N/A')}")
                        print(f"Address: {location.get('address', 'N/A')}")
                        print(f"Contact: {location.get('contact', 'N/A')}")
                    break
    else:
        print("No structured service center data found!")

if __name__ == "__main__":
    asyncio.run(main()) 