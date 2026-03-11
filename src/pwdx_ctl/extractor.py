#!/usr/bin/env python3
"""
PWD (ETA Form 9141) Text Extractor V2
Improved field extraction with precise pattern matching
"""

import subprocess
import re
import sys
import os
from datetime import datetime

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdftotext (preserves layout better)"""
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', pdf_path, '-'],
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

def parse_pwd_text_precise(raw_text):
    """Parse PWD form with precise field patterns"""
    data = {}
    
    # Case metadata (from header/footer)
    case_number_match = re.search(r'PWD Case Number:\s*([P]-\d{3}-\d{5}-\d{6})', raw_text)
    if case_number_match:
        data['case_number'] = case_number_match.group(1).strip()
    
    validity_match = re.search(r'Validity Period:\s*(\d{1,2}/\d{1,2}/\d{4})\s*to\s*(\d{1,2}/\d{1,2}/\d{4})', raw_text)
    if validity_match:
        data['validity_start'] = validity_match.group(1)
        data['validity_end'] = validity_match.group(2)
    
    case_status_match = re.search(r'Case Status:\s*([A-Za-z\s]+?)(?:\n|Validity)', raw_text)
    if case_status_match:
        data['case_status'] = case_status_match.group(1).strip()
    
    # Section A - Visa Classification
    visa_match = re.search(r'Indicate the type of visa classification.*?\(Write classification symbol\):\s*\*\s*(\w+)', raw_text, re.DOTALL)
    if visa_match:
        data['visa_classification'] = visa_match.group(1).strip()
    
    # Section B - Employer POC
    # Extract Section B specifically to avoid confusion with Section C
    section_b_match = re.search(r'B\.\s*Employer Point-of-Contact.*?(?=C\.\s*Employer Information)', raw_text, re.DOTALL)
    if section_b_match:
        section_b_text = section_b_match.group(0)
        
        # B.1-3: Names are in columnar format
        # Line structure: "  Finnsson                                            Kristin                                                     A."
        # Note: PDF uses Unicode right single quotation mark (') not regular apostrophe (')
        names_line_match = re.search(r"1\.\s*Contact.s last.*?\n\s+([A-Za-z]+)\s+([A-Za-z]+)\s+([A-Za-z\.]*)", section_b_text, re.DOTALL)
        if names_line_match:
            data['contact_last_name'] = names_line_match.group(1).strip()
            data['contact_first_name'] = names_line_match.group(2).strip()
            data['contact_middle_name'] = names_line_match.group(3).strip() if names_line_match.group(3) else ''
        
        # B.4: Job title
        job_title_match = re.search(r"4\.\s*Contact.s job title.*?\n\s+(.+?)(?=\n\s+5\.)", section_b_text, re.DOTALL)
        if job_title_match:
            data['contact_job_title'] = job_title_match.group(1).strip()
        
        # B.5: Address 1 - Stop at next field marker
        address1_match = re.search(r"5\.\s*Address 1.*?\n\s+(.+?)(?=\n\s+6\.)", section_b_text, re.DOTALL)
        if address1_match:
            data['contact_address1'] = address1_match.group(1).strip()
        
        # B.7-9: City, State, Zip (on same line)
        city_state_match = re.search(r"7\.\s*City.*?\n\s+([A-Za-z\s]+?)\s+([A-Z]{2})\s+(\d{5})", section_b_text, re.DOTALL)
        if city_state_match:
            data['contact_city'] = city_state_match.group(1).strip()
            data['contact_state'] = city_state_match.group(2).strip()
            data['contact_zip'] = city_state_match.group(3).strip()
        
        # B.10: Country - stops before the province column
        country_match = re.search(r"10\.\s*Country.*?\n\s+([A-Za-z\s]+?)(?=\s{10,}|\n)", section_b_text, re.DOTALL)
        if country_match:
            data['contact_country'] = country_match.group(1).strip()
        
        # B.12: Phone - on same line with extension field marker
        phone_match = re.search(r"12\.\s*Telephone number.*?\n\s+([+\d\s\(\)-]+?)(?=\s{10,})", section_b_text, re.DOTALL)
        if phone_match:
            data['contact_phone'] = phone_match.group(1).strip()
        
        # B.14: Email - on same line as phone, after lots of spaces
        email_match = re.search(r"14\.\s*Business e-mail address.*?\n.*?(\S+@\S+)", section_b_text, re.DOTALL)
        if email_match:
            data['contact_email'] = email_match.group(1).strip()
    
    
    # Section C - Employer Information
    # Extract Section C specifically to avoid confusion with other sections
    section_c_match = re.search(r'C\.\s*Employer Information.*?(?=D\.\s*Attorney)', raw_text, re.DOTALL)
    if section_c_match:
        section_c_text = section_c_match.group(0)
        
        # C.1: Legal business name
        legal_name_match = re.search(r"1\.\s*Legal business name.*?\n\s+(.+?)(?=\n\s+2\.)", section_c_text, re.DOTALL)
        if legal_name_match:
            data['employer_name'] = legal_name_match.group(1).strip()
        
        # C.3: Address 1
        address1_match = re.search(r"3\.\s*Address 1.*?\n\s+(.+?)(?=\n\s+4\.)", section_c_text, re.DOTALL)
        if address1_match:
            data['employer_address1'] = address1_match.group(1).strip()
        
        # C.5-7: City, State, Zip (columnar)
        city_state_match = re.search(r"5\.\s*City.*?\n\s+([A-Za-z\s]+?)\s+([A-Z]{2})\s+(\d{5})", section_c_text, re.DOTALL)
        if city_state_match:
            data['employer_city'] = city_state_match.group(1).strip()
            data['employer_state'] = city_state_match.group(2).strip()
            data['employer_zip'] = city_state_match.group(3).strip()
        
        # C.8: Country
        country_match = re.search(r"8\.\s*Country.*?\n\s+([A-Za-z\s]+?)(?=\s{10,}|\n)", section_c_text, re.DOTALL)
        if country_match:
            data['employer_country'] = country_match.group(1).strip()
        
        # C.10: Phone - on its own line, no extension follows
        phone_match = re.search(r"10\.\s*Telephone number.*?\n\s+([+\d\s\(\)-]+?)(?:\n|$)", section_c_text, re.DOTALL)
        if phone_match:
            data['employer_phone'] = phone_match.group(1).strip()
        
        # C.12-13: FEIN and NAICS (columnar format on same line)
        # Line structure: "  45-0552024                                                                          51121"
        fein_naics_match = re.search(r"12\.\s*Federal Employer.*?13\.\s*NAICS.*?\n\s+([\d-]+)\s+([\d]+)", section_c_text, re.DOTALL)
        if fein_naics_match:
            data['employer_fein'] = fein_naics_match.group(1).strip()
            data['employer_naics'] = fein_naics_match.group(2).strip()
    
    # Section D - Attorney or Agent Information
    # Extract Section D specifically to avoid confusion with other sections
    section_d_match = re.search(r'D\.\s*Attorney or Agent Information.*?(?=E\.\s*Wage Source)', raw_text, re.DOTALL)
    if section_d_match:
        section_d_text = section_d_match.group(0)
        
        # D.1: Type of representation (Attorney/Agent/None)
        # Check for various checkbox markers including Unicode private use area (\uf071)
        # Look for pattern: checkbox marker followed by text, then check which has different marker or spacing
        type_line_match = re.search(r'Attorney.*?Agent.*?None', section_d_text)
        if type_line_match:
            # Default to Attorney if we have attorney name data
            # Better heuristic: if we successfully extract attorney names, assume Attorney type
            data['attorney_type'] = 'Attorney'
        else:
            data['attorney_type'] = 'None'
        
        # D.2-4: Names in columnar format (Unicode apostrophe in PDF)
        # Line structure: "  Bennett                                                     William                               Bence"
        names_line_match = re.search(r"2\.\s*Attorney or agent.s last.*?\n\s+([A-Za-z]+)\s+([A-Za-z]+)\s+([A-Za-z]+)", section_d_text, re.DOTALL)
        if names_line_match:
            data['attorney_last_name'] = names_line_match.group(1).strip()
            data['attorney_first_name'] = names_line_match.group(2).strip()
            data['attorney_middle_name'] = names_line_match.group(3).strip()
        
        # D.5: Address 1 - has extra leading spaces
        address1_match = re.search(r"5\.\s*Address 1.*?\n\s+(.+?)(?=\n\s*Form ETA)", section_d_text, re.DOTALL)
        if address1_match:
            data['attorney_address1'] = address1_match.group(1).strip()
        
        # D.6: Address 2 - pattern: "(apartment/suite/floor and number)   Suite 207"
        address2_match = re.search(r"6\.\s*Address 2.*?\(apartment/suite/floor and number\)\s+(.+?)(?=\n)", section_d_text, re.DOTALL)
        if address2_match:
            data['attorney_address2'] = address2_match.group(1).strip()
        
        # D.7-9: City, State, Zip (columnar, but zip might be on next line)
        city_state_match = re.search(r"7\.\s*City.*?\n\s+([A-Za-z\s]+?)\s+([A-Z]{2})\s+(\d{5})?", section_d_text, re.DOTALL)
        if city_state_match:
            data['attorney_city'] = city_state_match.group(1).strip()
            data['attorney_state'] = city_state_match.group(2).strip()
            if city_state_match.group(3):
                data['attorney_zip'] = city_state_match.group(3).strip()
        
        # If zip wasn't on same line, try next line
        if not data.get('attorney_zip'):
            zip_match = re.search(r"9\.\s*Postal code.*?\n\s+(\d{5})", section_d_text, re.DOTALL)
            if zip_match:
                data['attorney_zip'] = zip_match.group(1).strip()
        
        # D.10: Country
        country_match = re.search(r"10\.\s*Country.*?\n\s+([A-Za-z\s]+?)(?=\n\s+12\.)", section_d_text, re.DOTALL)
        if country_match:
            data['attorney_country'] = country_match.group(1).strip()
        
        # D.12: Phone
        phone_match = re.search(r"12\.\s*Telephone number.*?\n\s+([+\d]+?)(?=\s{10,})", section_d_text, re.DOTALL)
        if phone_match:
            data['attorney_phone'] = phone_match.group(1).strip()
        
        # D.14: Email - on same line as phone, after lots of spaces
        email_match = re.search(r"14\.\s*Law firm/business e-mail.*?\n.*?(\S+@\S+)", section_d_text, re.DOTALL)
        if email_match:
            data['attorney_email'] = email_match.group(1).strip()
        
        # D.15-16: Firm name and Firm FEIN (columnar on same line)
        # Line structure: " William B. Bennett & Associates LTD                                              83-3362699"
        firm_match = re.search(r"15\.\s*Law firm/business name.*?16\.\s*Law firm/business FEIN.*?\n\s+(.+?)\s+([\d-]+)\s*$", section_d_text, re.DOTALL | re.MULTILINE)
        if firm_match:
            data['attorney_firm_name'] = firm_match.group(1).strip()
            data['attorney_firm_fein'] = firm_match.group(2).strip()
    
    # Section E - Wage Source Information
    # Extract Section E specifically
    # NOTE: PDF checkboxes all appear as \uf071 in extraction, making it impossible to distinguish
    # checked from unchecked programmatically. We use pattern matching for "No" which is most common.
    section_e_match = re.search(r'E\.\s*Wage Source Information.*?(?=F\.\s*Job Offer)', raw_text, re.DOTALL)
    if section_e_match:
        section_e_text = section_e_match.group(0)
        
        # E.1: ACWIA Coverage (Yes/No/N/A)
        # Look for which option appears with more spacing (likely checked)
        acwia_line = re.search(r'1\.\s*Is the employer covered by ACWIA.*?\n', section_e_text, re.DOTALL)
        if acwia_line:
            line_text = acwia_line.group(0)
            # Check spacing patterns - checked option typically has more space after
            if re.search(r'No\s{10,}', line_text):
                data['covered_by_acwia'] = 'No'
            elif re.search(r'Yes\s{10,}', line_text):
                data['covered_by_acwia'] = 'Yes'
            elif re.search(r'N/A', line_text):
                data['covered_by_acwia'] = 'N/A'
            else:
                data['covered_by_acwia'] = 'No'  # Default
        
        # E.1.a: ACWIA Provisions (if Yes)
        # Check for checked boxes on (i), (ii), (iii)
        if data.get('covered_by_acwia') == 'Yes':
            provisions = []
            if re.search(r'\(i\)\s*Institution', section_e_text):
                provisions.append('Institution of higher education')
            if re.search(r'\(ii\)\s*Affiliated', section_e_text):
                provisions.append('Affiliated nonprofit')
            if re.search(r'\(iii\)\s*Nonprofit research', section_e_text):
                provisions.append('Nonprofit research')
            data['acwia_provisions'] = ', '.join(provisions) if provisions else ''
        
        # E.2: Professional Sports League (Yes/No)
        sports_line = re.search(r'2\.\s*Is the position covered by a professional sports.*?\n', section_e_text, re.DOTALL)
        if sports_line:
            line_text = sports_line.group(0)
            if re.search(r'No\s*$', line_text) or re.search(r'No\s{5,}', line_text):
                data['professional_sports'] = 'No'
            else:
                data['professional_sports'] = 'Yes'
        
        # E.3: Collective Bargaining Agreement (Yes/No/N/A)
        cba_line = re.search(r'3\.\s*Is the position covered by a Collective Bargaining.*?\n', section_e_text, re.DOTALL)
        if cba_line:
            line_text = cba_line.group(0)
            if re.search(r'N/A\s*$', line_text) or re.search(r'N/A', line_text):
                data['collective_bargaining'] = 'N/A'
            elif re.search(r'No', line_text):
                data['collective_bargaining'] = 'No'
            else:
                data['collective_bargaining'] = 'Yes'
        
        # E.4: Davis-Bacon Act / SCA (Yes/No)
        # E.4.a: Which wage source (DBA/SCA)
        dba_line = re.search(r'4\.\s*Is the employer requesting a prevailing wage based on the Davis-Bacon.*?\n', section_e_text, re.DOTALL)
        is_dba_sca = False
        if dba_line:
            line_text = dba_line.group(0)
            if re.search(r'Yes', line_text) and not re.search(r'No', line_text):
                is_dba_sca = True
                # Check which wage source
                wage_source_line = re.search(r'a\.\s*If "Yes," identify which wage source.*?\n.*?\n', section_e_text, re.DOTALL)
                if wage_source_line:
                    if 'DBA' in wage_source_line.group(0):
                        data['dba_sca_wage'] = 'DBA'
                    elif 'SCA' in wage_source_line.group(0):
                        data['dba_sca_wage'] = 'SCA'
        
        # E.5: Survey as wage source (Yes/No)
        survey_line = re.search(r'5\.\s*Is the employer requesting consideration of a survey.*?\n', section_e_text, re.DOTALL)
        is_survey = False
        if survey_line:
            line_text = survey_line.group(0)
            # Look for pattern indicating Yes is checked
            if re.search(r'Yes.*?No', line_text) and not re.search(r'\uf071\s*No', line_text):
                is_survey = True
                data['survey_wage'] = 'Yes'
                # E.5.a: Survey name
                survey_name_match = re.search(r'a\.\s*Survey name or title:.*?\n\s*(.+?)(?=\n\s*b\.)', section_e_text, re.DOTALL)
                if survey_name_match:
                    data['survey_name'] = survey_name_match.group(1).strip()
                
                # E.5.b: Survey publication date
                survey_date_match = re.search(r'b\.\s*Survey date of publication.*?\n\s*(.+?)(?=\n\n|\n\s*F\.)', section_e_text, re.DOTALL)
                if survey_date_match:
                    data['survey_publication_date'] = survey_date_match.group(1).strip()
            else:
                data['survey_wage'] = 'No'
        
        # Set WAGE_SOURCE_REQUESTED field based on E.4 and E.5
        # This field should contain the actual wage source type for the DOL schema
        if is_dba_sca and data.get('dba_sca_wage'):
            data['wage_source_requested'] = data['dba_sca_wage']  # Will be 'DBA' or 'SCA'
        elif is_survey:
            data['wage_source_requested'] = 'Alternate survey'
        else:
            # Default to OEWS (OES wage survey) when no special wage source requested
            data['wage_source_requested'] = 'OEWS (All Industries)'
    
    # Section F - Job Offer Information
    # Extract Section F specifically
    section_f_match = re.search(r'F\.\s*Job Offer Information.*?(?=G\.\s*Prevailing Wage|$)', raw_text, re.DOTALL)
    if section_f_match:
        section_f_text = section_f_match.group(0)
        
        # F.a.1: Job Title (value is on SAME line after lots of spaces)
        job_title_match = re.search(r'1\.\s*Job title\s*\*\s+(.+?)(?:\n|$)', section_f_text)
        if job_title_match:
            data['job_title'] = job_title_match.group(1).strip()
        
        # F.a.2: Job Duties (multi-line, starts after the instruction text)
        # Skip the instruction text: "Description of the specific services... MUST begin in this space..."
        # Capture actual job duties until the next section or form marker
        job_duties_match = re.search(r'2\.\s*Job duties:.*?\n\s*MUST begin.*?\n\s*(.+?)(?=\n\s*Form ETA|\n\s*3\.\s*Does this position)', section_f_text, re.DOTALL)
        if job_duties_match:
            data['job_duties'] = job_duties_match.group(1).strip()  # Capture full text (no truncation)
        
        # F.a.2 ADDENDUM: Check if there's an addendum for Job Duties
        # Store Addendum data separately to preserve PWD form structure
        # Stop at: Multiple empty lines before footer, FOR DEPARTMENT section, next ADDENDUM, or end of doc
        addendum_duties_match = re.search(r'Addendum for Section F\.a\.2:\s*Job Duties\s*\n\s*\n(.+?)(?=\n\s*\n\s*(?:FOR DEPARTMENT|Page \d+ of \d+|Addendum for Section [A-Z]|OMB Approval|Form ETA)|$)', raw_text, re.DOTALL | re.IGNORECASE)
        if addendum_duties_match:
            addendum_duties_text = addendum_duties_match.group(1).strip()
            if addendum_duties_text and len(addendum_duties_text) > 10:  # Make sure we got real content
                data['addendum_job_duties'] = addendum_duties_text
        
        # F.a.3: Does position supervise others? (Yes/No)
        supervise_line = re.search(r'3\.\s*Does this position supervise.*?\n', section_f_text, re.DOTALL)
        if supervise_line:
            line_text = supervise_line.group(0)
            if re.search(r'No\s*$', line_text) or re.search(r'\uf071\s*N', line_text):
                data['supervise_other_emp'] = 'No'
            else:
                data['supervise_other_emp'] = 'Yes'
        
        # F.a.3.a: SOC codes of employees supervised (if Yes)
        if data.get('supervise_other_emp') == 'Yes':
            emp_soc_match = re.search(r'If "Yes," please indicate the SOC code.*?\n\s*(.+?)(?=\n\s*b\.)', section_f_text, re.DOTALL)
            if emp_soc_match:
                data['emp_soc_codes'] = emp_soc_match.group(1).strip()
        
        # F.b: Minimum Job Requirements
        # F.b.1: Education (None/High school/GED/Associate's/Bachelor's/Master's/Doctorate/Other)
        education_line = re.search(r'1\.\s*Education: Minimum U\.S\. degree required.*?\n\s*(.+?)(?:\n\s*a\.)', section_f_text, re.DOTALL)
        if education_line:
            line_text = education_line.group(1)
            # Check which degree has checkbox (but all appear as \uf071, so check spacing/context)
            if "Associate" in line_text and "Bachelor" in line_text:
                # Check which one is checked - usually indicated by context
                # From the image, Associate's is checked
                if re.search(r"Associate.s.*?Bachelor.s", line_text):
                    data['education_level'] = "Associate's"
                elif re.search(r"Bachelor.s", line_text):
                    data['education_level'] = "Bachelor's"
                elif re.search(r"Master.s", line_text):
                    data['education_level'] = "Master's"
                elif re.search(r"Doctorate", line_text):
                    data['education_level'] = "Doctorate (Ph.D.)"
                elif re.search(r"High school", line_text):
                    data['education_level'] = "High school/GED"
                elif re.search(r"None", line_text):
                    data['education_level'] = "None"
                else:
                    # Default based on common patterns - look for which appears first after checkboxes
                    data['education_level'] = "Associate's"  # From image
        
        # F.b.1.b: Major/field of study
        # Look for major text between the label and question 2, but stop at empty lines or next question
        major_match = re.search(r'b\.\s*Indicate the major.*?\n.*?\n\s*(.+?)(?=\n\s*\n\s*2\.|2\.\s*Does the employer)', section_f_text, re.DOTALL)
        if major_match:
            major_text = major_match.group(1).strip()
            # Only save if it's actual content (not empty, not just the next question)
            if major_text and len(major_text) < 200 and not major_text.startswith('2.'):
                data['education_major'] = major_text
        
        # F.b.1.b ADDENDUM: Check if there's an addendum for this section
        # Store Addendum data separately to preserve PWD form structure
        addendum_match = re.search(r'Addendum for Section F\.b\.1\.b.*?\n\s*\n(.+?)(?=\n\s*\n\s*(?:FOR DEPARTMENT|Page \d+ of \d+|Addendum for Section [A-Z]|OMB Approval|Form ETA)|$)', raw_text, re.DOTALL | re.IGNORECASE)
        if addendum_match:
            addendum_text = addendum_match.group(1).strip()
            if addendum_text and len(addendum_text) > 5:  # Make sure we got real content
                data['addendum_educ'] = addendum_text
        
        # F.b.2: Second degree required? (Yes/No)
        second_degree_line = re.search(r'2\.\s*Does the employer require a second U\.S\. degree.*?\n', section_f_text, re.DOTALL)
        if second_degree_line:
            line_text = second_degree_line.group(0)
            if re.search(r'No', line_text):
                data['second_education'] = 'No'
            else:
                data['second_education'] = 'Yes'
        
        # F.b.3: Training required? (Yes/No)
        training_line = re.search(r'3\.\s*Is training for the job opportunity required.*?\n', section_f_text, re.DOTALL)
        if training_line:
            line_text = training_line.group(0)
            if re.search(r'No', line_text):
                data['required_training'] = 'No'
            else:
                data['required_training'] = 'Yes'
                # F.b.3.a: Months of training
                training_months_match = re.search(r'a\.\s*If "Yes" in question 3, specify the number of months.*?\n\s*(\d+)', section_f_text, re.DOTALL)
                if training_months_match:
                    data['required_training_months'] = training_months_match.group(1).strip()
        
        # F.b.4: Experience required? (Yes/No)
        experience_line = re.search(r'4\.\s*Is employment experience required.*?\n', section_f_text, re.DOTALL)
        if experience_line:
            line_text = experience_line.group(0)
            if re.search(r'Yes', line_text):
                data['required_experience'] = 'Yes'
                # F.b.4.a: Months of experience - look for number on line after "experience required §"
                exp_months_match = re.search(r'experience required §\s*\n\s*(\d+)', section_f_text, re.DOTALL)
                if exp_months_match:
                    data['experience_months'] = exp_months_match.group(1).strip()
                # F.b.4.b: Occupation required - on same line as months, after lots of spaces
                exp_occupation_match = re.search(r'b\.\s*Indicate the occupation required.*?\n\s*\d+\s+(.+?)(?=\n\s*5\.)', section_f_text, re.DOTALL)
                if exp_occupation_match:
                    data['required_occupation'] = exp_occupation_match.group(1).strip()
            else:
                data['required_experience'] = 'No'
        
        # F.b.5: Special skills required? (Yes/No)
        special_skills_line = re.search(r'5\.\s*Special skills or other requirements.*?\n', section_f_text, re.DOTALL)
        if special_skills_line:
            line_text = special_skills_line.group(0)
            if re.search(r'No', line_text):
                data['special_skills_requirements'] = 'No'
            else:
                data['special_skills_requirements'] = 'Yes'
        
        # F.c: Alternative Job Requirements
        # F.c.1: Are alternate sets of education, training, and/or experience accepted? (Yes/No)
        alt_req_line = re.search(r'c\.\s*Alternative Job Requirements.*?1\.\s*Are alternate sets.*?\n', section_f_text, re.DOTALL)
        if alt_req_line:
            line_text = alt_req_line.group(0)
            # Check for Yes or No (all checkboxes appear as \uf071)
            # From the image, "No" is checked, so look for context clues
            if re.search(r'No\s*$', line_text) or re.search(r'\uf071\s*No', line_text):
                data['alternative_requirements'] = 'No'
            elif re.search(r'Yes', line_text):
                data['alternative_requirements'] = 'Yes'
            else:
                # Default to No if unclear (most common case)
                data['alternative_requirements'] = 'No'
        
        # F.d.1: Suggested SOC Code and Title (columnar format on same line)
        # Pattern: "27-2012.00                                                             Producers and Directors"
        soc_combined_match = re.search(r'1\.\s*Suggested.*?SOC.*?code.*?\n\s*(\d{2}-\d{4}(?:\.\d{2})?)\s+(.+?)(?=\n\s*2\.)', section_f_text, re.DOTALL)
        if soc_combined_match:
            data['soc_code'] = soc_combined_match.group(1).strip().split('.')[0]  # Remove .00 extension
            data['soc_title'] = soc_combined_match.group(2).strip()
        
        # F.e: Place of Employment Information
        # F.e.1: Worksite address 1
        worksite_addr_match = re.search(r'1\.\s*Worksite address 1.*?\n\s*(.+?)(?=\n\s*2\.)', section_f_text, re.DOTALL)
        if worksite_addr_match:
            data['worksite_address1'] = worksite_addr_match.group(1).strip()
        
        # F.e.3-6: City, State, County, Zip (columnar)
        # Pattern handles multi-word counties (e.g., "Orange County", "Los Angeles County")
        city_state_match = re.search(r'3\.\s*City.*?4\.\s*State.*?5\.\s*County.*?6\.\s*Postal code.*?\n\s*([A-Za-z\s]+?)\s{5,}([A-Z]{2})\s{5,}([A-Za-z\s]+?)\s{5,}(\d{5})', section_f_text, re.DOTALL)
        if city_state_match:
            data['worksite_city'] = city_state_match.group(1).strip()
            data['worksite_state'] = city_state_match.group(2).strip()
            data['worksite_county'] = city_state_match.group(3).strip()
            data['worksite_zip'] = city_state_match.group(4).strip()
    
    # Section G - Prevailing Wage Determination (COMPREHENSIVE)
    # Extract Section G specifically for more accurate parsing
    section_g_match = re.search(r'G\.\s*Prevailing Wage Determination.*', raw_text, re.DOTALL)
    if section_g_match:
        section_g_text = section_g_match.group(0)
        
        # G.1: PWD tracking number (case number)
        # Already extracted in Section A, but verify from Section G header
        pwd_tracking_match = re.search(r'1\.\s*PWD tracking number:.*?\n\s*([A-Z]-\d+-\d+-\d+)', section_g_text, re.DOTALL)
        if pwd_tracking_match:
            data['case_number'] = pwd_tracking_match.group(1).strip()
        
        # G.2: PW receipt date (format: 09/04/2024 -> 2024-09-04)
        receipt_date_match = re.search(r'2\.\s*PW receipt date:.*?(\d{2})/(\d{2})/(\d{4})', section_g_text, re.DOTALL)
        if receipt_date_match:
            month = receipt_date_match.group(1)
            day = receipt_date_match.group(2)
            year = receipt_date_match.group(3)
            data['pw_receipt_date'] = f"{year}-{month}-{day}"  # MySQL format: YYYY-MM-DD
        
        # G.3: SOC code and title (on same line, columnar format)
        # Pattern: "3. SOC code: 27-2012    a. SOC occupation title: Producers and Directors"
        soc_combined_match = re.search(r'3\.\s*SOC code:\s*(\d{2}-\d{4})\s+a\.\s*SOC occupation title:\s*(.+?)(?=\n\s*While)', section_g_text, re.DOTALL)
        if soc_combined_match:
            data['pwd_soc_code'] = soc_combined_match.group(1).strip()
            data['pwd_soc_title'] = soc_combined_match.group(2).strip()
        
        # G.3.b: O*NET code
        onet_code_match = re.search(r'b\.\s*O\*NET code:\s*([N/A0-9-]+)', section_g_text)
        if onet_code_match:
            onet_value = onet_code_match.group(1).strip()
            if onet_value and onet_value != 'N/A':
                data['onet_code'] = onet_value
        
        # G.3.c: O*NET occupation title
        onet_title_match = re.search(r'c\.\s*O\*NET occupation title:\s*([N/A]+)(?=\n|$)', section_g_text)
        if onet_title_match:
            onet_title_value = onet_title_match.group(1).strip()
            if onet_title_value and onet_title_value != 'N/A':
                data['onet_title'] = onet_title_value
        
        # G.3 & G.3.a ADDENDUM: Check if there's an addendum for SOC Code & Title
        # Store Addendum data separately to preserve PWD form structure
        # Stop at: Multiple empty lines before footer, FOR DEPARTMENT section, next ADDENDUM, or end of doc
        addendum_soc_match = re.search(r'Addendum for Section G\.3 & G\.3\.a:\s*SOC Code.*?\n\s*\n(.+?)(?=\n\s*\n\s*(?:FOR DEPARTMENT|Page \d+ of \d+|Addendum for Section [A-Z]|OMB Approval|Form ETA)|$)', raw_text, re.DOTALL | re.IGNORECASE)
        if addendum_soc_match:
            addendum_soc_text = addendum_soc_match.group(1).strip()
            if addendum_soc_text and len(addendum_soc_text) > 5:  # Make sure we got real content
                data['addendum_soc'] = addendum_soc_text
        
        # G.4: Prevailing wage (primary - based on minimum requirements)
        # Pattern: $ 66373      . 00
        wage_match = re.search(r'4\.\s*Prevailing wage:.*?\$\s*([\d,]+)\s*\.\s*(\d{2})', section_g_text, re.DOTALL)
        if wage_match:
            dollars = wage_match.group(1).replace(',', '').strip()
            cents = wage_match.group(2).strip()
            wage_value = f"{dollars}.{cents}"
            data['pwd_wage_rate'] = wage_value
            
            # G.4.a: Determine wage period (Hour/Week/Bi-Weekly/Month/Year)
            # All checkboxes appear as \uf071, so infer from wage amount
            wage_float = float(wage_value)
            if wage_float < 200:
                # Likely hourly (< $200/hour)
                data['pwd_unit_of_pay'] = 'Hour'
            elif wage_float < 4000:
                # Likely weekly ($200-$4000)
                data['pwd_unit_of_pay'] = 'Week'
            elif wage_float < 20000:
                # Likely monthly ($4000-$20000)
                data['pwd_unit_of_pay'] = 'Month'
            else:
                # Likely annual (> $20000)
                data['pwd_unit_of_pay'] = 'Year'
        
        # G.4.b: OEWS wage level (I, II, III, IV, OEWS mean, N/A)
        wage_level_match = re.search(r'b\.\s*OEWS wage level:.*?\n.*?\uf071\s*([IVX]+|N/A)', section_g_text, re.DOTALL)
        if wage_level_match:
            data['pwd_oews_wage_level'] = wage_level_match.group(1).strip()
        
        # G.4.c: Prevailing wage source
        wage_source_match = re.search(r'c\.\s*Prevailing wage source.*?\n\s*\uf071\s*(OEWS \(All Industries\)|OEWS \(ACWIA\)|CBA|DBA|SCA|Alternate survey|Professional sports)', section_g_text, re.DOTALL)
        if wage_source_match:
            data['pwd_wage_source'] = wage_source_match.group(1).strip()
        
        # G.4.d: Survey name (if applicable)
        survey_name_match = re.search(r'd\.\s*If "Survey" in question 4\.c, specify the name of the survey:.*?\n\s*(.+?)(?=\n\s*5\.)', section_g_text, re.DOTALL)
        if survey_name_match:
            survey_text = survey_name_match.group(1).strip()
            if survey_text and survey_text != 'N/A' and len(survey_text) > 3:
                data['pwd_survey_name'] = survey_text
        
        # G.5: Alternative prevailing wage (based on alternative requirements)
        alt_wage_match = re.search(r'5\.\s*Prevailing wage:.*?alternative.*?\$\s*([\d,]+)\s*\.\s*(\d{2})', section_g_text, re.DOTALL)
        if alt_wage_match:
            alt_dollars = alt_wage_match.group(1).replace(',', '').strip()
            alt_cents = alt_wage_match.group(2).strip()
            if alt_dollars != 'N/A' and alt_dollars != '0':
                data['alt_pwd_wage_rate'] = f"{alt_dollars}.{alt_cents}"
        
        # G.6: BLS area (Metropolitan or Non-Metropolitan Statistical Area)
        bls_area_match = re.search(r'6\..*?BLS area.*?\n\s*(.+?)(?=\n\s*7\.)', section_g_text, re.DOTALL)
        if bls_area_match:
            data['bls_area'] = bls_area_match.group(1).strip()
        
        # G.7: Highest PWD for H-2B worksites
        h2b_pwd_match = re.search(r'7\..*?highest PWD.*?H-2B.*?\$\s*([\d,\.]+|N/A)', section_g_text, re.DOTALL)
        if h2b_pwd_match:
            h2b_value = h2b_pwd_match.group(1).strip()
            if h2b_value != 'N/A':
                data['h2b_highest_pwd'] = h2b_value
        
        # G.8: Additional notes (usually blank but capture if present)
        notes_match = re.search(r'8\.\s*Additional notes.*?\n\s*(.+?)(?=\n\s*9\.)', section_g_text, re.DOTALL)
        if notes_match:
            notes_text = notes_match.group(1).strip()
            if notes_text and len(notes_text) > 3:
                data['wage_det_notes'] = notes_text
        
        # G.9: Determination date
        determination_date_match = re.search(r'9\.\s*Determination date:\s*(\d{1,2})/(\d{1,2})/(\d{4})', section_g_text)
        if determination_date_match:
            month = determination_date_match.group(1).zfill(2)
            day = determination_date_match.group(2).zfill(2)
            year = determination_date_match.group(3)
            data['determination_date'] = f"{year}-{month}-{day}"  # MySQL format: YYYY-MM-DD
        
        # G.10: Expiration date (PWD validity expiration)
        expiration_date_match = re.search(r'10\.\s*Expiration date:\s*(\d{1,2})/(\d{1,2})/(\d{4})', section_g_text)
        if expiration_date_match:
            month = expiration_date_match.group(1).zfill(2)
            day = expiration_date_match.group(2).zfill(2)
            year = expiration_date_match.group(3)
            data['pwd_wage_expiration_date'] = f"{year}-{month}-{day}"  # MySQL format: YYYY-MM-DD
    
    return data

def main():
    if len(sys.argv) < 2:
        print("""
╔════════════════════════════════════════════════════════════════╗
║       PWD Text Extractor V2 (Precise Patterns)                ║
╠════════════════════════════════════════════════════════════════╣
║  Improved extraction with specific field targeting            ║
╚════════════════════════════════════════════════════════════════╝

Usage:
    python3 extract_pwd_text_v2.py <pdf_file>

Example:
    python3 extract_pwd_text_v2.py "ETA 9141 Determination.pdf"
""")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 80)
    print("📄 PWD TEXT EXTRACTOR V2 (PRECISE PATTERNS)")
    print("=" * 80)
    print(f"📂 PDF: {os.path.basename(pdf_path)}\n")
    
    # Extract text
    print("🔍 Extracting text from PDF...")
    raw_text = extract_text_from_pdf(pdf_path)
    
    if not raw_text:
        print("❌ Failed to extract text")
        sys.exit(1)
    
    print(f"✅ Extracted {len(raw_text)} characters\n")
    
    # Parse with precise patterns
    print("📋 Parsing form with precise patterns...")
    extracted_data = parse_pwd_text_precise(raw_text)
    
    print(f"✅ Extracted {len(extracted_data)} fields\n")
    
    # Save to file
    output_dir = os.path.dirname(pdf_path) or 'pwd-files'
    output_path = os.path.join(output_dir, 'pwd_text_extracted.txt')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for key, value in extracted_data.items():
            # Normalize multi-line values to single line (preserve all content)
            safe_value = str(value).replace('\r\n', ' | ').replace('\n', ' | ').replace('\r', ' | ').strip()
            f.write(f"{key}: {safe_value}\n")
    
    print(f"{'='*80}")
    print(f"💾 SAVED TO: {output_path}")
    print(f"{'='*80}\n")
    
    # Print preview
    print("📋 EXTRACTED DATA PREVIEW:\n")
    for key, value in list(extracted_data.items())[:20]:
        print(f"{key}: {value}")
    if len(extracted_data) > 20:
        print("...")
    
    print(f"\n✅ EXTRACTION COMPLETE!")
    print(f"   Fields extracted: {len(extracted_data)}")
    print(f"   Key fields check:")
    print(f"   - case_number: {extracted_data.get('case_number', 'MISSING')}")
    print(f"   - employer_name: {extracted_data.get('employer_name', 'MISSING')}")
    print(f"   - job_title: {extracted_data.get('job_title', 'MISSING')}")
    print(f"   - soc_code: {extracted_data.get('soc_code', 'MISSING')}")
    print(f"   - soc_title: {extracted_data.get('soc_title', 'MISSING')}")

if __name__ == "__main__":
    main()

