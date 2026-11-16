## 1. Project Overview & Problem Statement

We run a software company called **Scalabox Technology**, where we develop and provide various software products and services. One of our products is a Hospital Management System (HMS).

To find potential customers for our products and services, we currently search Google for different types of businesses, such as hospitals, medical centres, clinics, and other companies.

However, the business information available online is not always reliable. Some phone numbers are fake, outdated, or inactive. Email addresses may be incorrect or unverified, and business websites and other details may also be outdated.

Because of this, finding genuine businesses and collecting accurate contact information takes a lot of time and effort. It is also difficult to identify which businesses are actually relevant to our products and services.

To solve this problem, we are building an **Evidence-Based Location-Aware Business Lead Discovery Tool**.

This tool will help users discover different types of businesses within a selected geographical area, collect their publicly available business information and contact details, and verify the information using reliable sources. It will also help identify potential customers based on how relevant their business is to the products or services being offered.

The main goal is to build a flexible lead discovery tool that can be used not just for HMS, but also for different software products, services, industries, and business needs.

-------- Example --------

User	        - Scalabox Technology (Our Company)
Product	        - Hospital Management System (HMS)
Target Customer - Hospitals, Clinics, Medical Centres, etc.
Main Problem	- Finding genuine potential customers with accurate and reliable business information.
Solution	    - Evidence-Based Business Lead Discovery Tool

## 2. System Architecture

flowchart TD
    A["Browser: area, radius, product, category"] --> B["FastAPI: Pydantic validate"]
    B -->|bad input| B1["422 error to browser"]
    B -->|ok| C["Save search in SQLite"]
    C --> D["Search id + stream open"]
    D --> E["Nominatim: area text to lat/lng"]
    E -->|no match| E1["Area not found, stop"]
    E -->|many| E2["User picks one"]
    E2 --> F
    E -->|one| F["Get data: Google + OSM"]
    F -->|one down| F1["Continue with other source + note"]
    F -->|both down| F2["Show Error, stop"]
    F --> G["Save raw data + retrieval time"]
    F1 --> G
    G --> H["Normalize name, address, phone"]
    H --> I["Distance filter: haversine, outside radius removed"]
    I --> J["Remove Duplicates: rapidfuzz"]
    J -->|no duplicate| K
    J -->|doubt| J1["Flag as possible duplicate, no auto merge"]
    J -->|same| J2["Merge, keep sources"]
    J1 --> K["Exclusions + count"]
    J2 --> K
    K --> L["Robots.txt check"]
    L -->|blocked / no site| L1["Website: Not found"]
    L -->|allowed| L2["Fetch page: name, address, public phone/email"]
    L1 --> M["Verifier: rules only"]
    L2 --> M
    M --> M1{"Status"}
    M1 -->|closed / no source| R["rejected"]
    M1 -->|2 sources| V["verified"]
    M1 -->|1 source| P["partially_verified"]
    M1 -->|conflict| U["unverified"]
    R --> S["Score"]
    V --> S
    P --> S
    U --> S
    S --> T["Write reason"]
    T --> W["Save evidence"]
    W --> X["Show card"]
    X -->|next lead| L
    X -->|no more leads| Y["Search complete"]
    Y --> Z["History, CSV, correction, re-check"]

## 3. End-to-End Data Flow

Browser : The user gives the input (area, radius, product, category).

Server  : The Pydantic library validates the input. It checks data types, so if the user gives area = 11354 (an integer) instead of a string, it will give an error. Then the server saves the search in the database and returns a search id.

Nominatim : It converts the area text to lat/lng. For example( if user give Coimbatore it will convert (Latitude - 11.0168
Longitude - 76.9558)) (no match = stop, many matches = user picks one).

External : Google Places and OSM Overpass are called in parallel (one down = continue with a note, both down = stop).

Storage: Raw data and retrieval time are saved. For example (source - Google Places
retrieved_at - 10 Nov 2026, 3:45 PM).

Normalizer : It is used to clean the data. For example, (Google - VIJAY HOS and OSM - Vijay Hospital), it gives Vijay Hospital.

Distance Filter : It will remove the places that are outside the radius using Haversine.

Duplicate Filter: Identify duplicate businesses using RapidFuzz. Merge confirmed duplicates while preserving source details. Flag uncertain matches.

Exclusion Filter : Apply user exclusions and filters.

Website Verification : Check the robots.txt file. If it allows access, read the website; otherwise, mark the website as not accessible.

Verification Engine: Assign verification status based on available evidence.
- Verified => 2 sources
- Partially Verified => 1 source
- Unverified => Conflict
- Rejected => No source

Relevance Scoring : Calculate lead score based on geographic match, category fit and evidence completeness.

Lead Explanation : Generate a reason explaining why the business may be a relevant prospect.

Evidence Storage : Store source URLs, evidence and verification details.

Final Results – Browser : Display lead cards, search history, CSV export, corrections and re-verification.

## 4. Technology Stack

| Technology | Why I chose it |


- Python 3.11+, FastAPI, Uvicorn          - To build the backend API and handle user requests.
- Pydantic                                - To validate the user inputs before processing them.
- HTML,CSS,JavaScript                     - To build a simple frontend and display the results one by one.
- SQLite                                  - To store search history, business records, evidence and verification details.
- httpx                                   - To send requests to external APIs and websites.
- BeautifulSoup4                          - To extract useful information from website HTML pages.
- robotparser (built-in)                  - To check robots.txt before accessing a website.
- RapidFuzz                               - To identify similar business names and find duplicate records.
- Haversine                               - To calculate distance and filter businesses based on the selected radius.
- Nominatim                               - To convert the entered location into latitude and longitude.
- Google Places API + OSM Overpass        - To discover businesses using two different data sources.
- pytest                                  - To test the application and check whether each component works correctly.


## 5. Risks and Tests

- 1. Incorrect Business Data   - Google and OSM may gives the wrong information like wrong address, wrong number 
Test: Provide a wrong address and check the verification status.

- 2. Wrong Duplicate Merge     - Two hospitals with the same name but different locations should not be merged into one. 
Test: Provide two hospitals with the same name but different addresses and check whether they remain separate records.

- 3.  Missing Data - May not find the business phone number. 
Test: Use a business without a phone number and check whether it displays Not Found instead of generating a number.

- 4. API Failure - Google API or OSM may fail. If one fails, search should continue using the other.
Test: Make one source unavailable and check whether the search continues using the available source.

- 5. Incorrect Website Association - May link a business to the wrong website. 
Test: Provide a business with an incorrect website URL and check whether the system detects the mismatch.


## 6. Milestone Plan with Measurable Completion Criteria

- Milestone:1 – Sources and Compliance

Connect Google Places API and OSM Overpass API.
Collect around 20 sample business details from one selected test location.
Store each business name, source URL and collection time in SQLite database.
Check and write down the terms of use, rate limits, attribution rules and data storage rules for both sources.
Done when: 20 businesses saved with source URL and time, and compliance notes are ready.

- Milestone:2 – Search, Geocoding and Cleaning

Take area, radius, product and category from user and validate it. Bad input like radius = "abc" give 422 error.
Convert area text to lat/lng using Nominatim. No match show "Area not found", many matches ask user to choose one.
Normalize names, addresses, phone numbers and website domains.
Remove the businesses which are outside the radius using haversine distance.
Dedupe the records. Same business in Google and OSM become one record with "found in 2 sources", doubtful ones are only flagged.
Apply exclusions and show the count with reason.
Done when: a 10 km search gives no result outside the radius, and duplicates are merged or flagged.

- Milestone:3 – Verification, Scoring and Evidence

Check business website only if robots.txt allow it.
Save every fact as evidence record with value, source and date. Missing data show "Not found".
Give one of four status (verified, partially_verified, unverified, rejected) using fixed Python rules, and save each decision in verification_events.Calculate relevance score with factor breakdown, keep it separate from status.
Write template reason using only evidence facts and mark it as inference.
Add user fact correction and re-check.
Done when: all test cases give the expected status and every fact have source and date.

- Milestone:4 – UI, Export and Testing

Build HTML/CSS/JS UI. Cards come one by one using SSE and old cards stay on the screen.
Add lead detail view, search history and CSV export with source URLs and status.
Test valid, duplicate, stale, conflicting, non-existent and no-result cases.
Prepare README, compliance notes, connector docs, methodology, test dataset, demo recording and sample CSV.
Done when: all tests pass and a reviewer can trace why each lead appeared.

## 7. Three Design Decisions I Made Independently

- Decision 1: One source is partially_verified, even if it has a website

If a business is found in only one source, I mark it as partially_verified. It does not matter if it has a website or not. I rejected two other options: making it verified when a matching website is found, and adding a fifth status for this case. The reason is the website link usually comes from the same source (like Google), so it is not a really independent proof. Also the brief already fixes four statuses, so I did not want to add a new one.

- Decision 2: If in doubt, flag it. Do not merge or delete

When two records look similar or an exclusion match is not clear, I only put a flag on the record. I rejected automatic merging of similar records and automatic removal of exclusion matches. The reason is a wrong merge or removal can hide a real lead and the user will not even know. A flag only gives one extra card, but nothing is lost. For confirmed exclusions I still show the count and reason.

- Decision 3: Verification uses fixed rules, not an LLM

The verifier is normal Python rules, like closed business becomes rejected. I rejected the idea of asking an LLM "is this business real". The reason is an LLM can invent facts and we cannot audit its answer. Rules are easy to explain and every decision is saved in verification_events, so a reviewer can check why a lead got its status.

## 8. Questions for the Task Owner

- 1. The brief says the LLM layer is optional. I plan to build the first version without an LLM: verification, scoring and the reason text will use fixed rules and a template. Is this acceptable? If you want an LLM later, it would only classify categories and summarize source text (never change status or score). Should that be a cloud API or a local model, and which one?

- 2.  If a business is found in only one source and has a matching website, I keep it as partially_verified. Is this okay or should it be verified?

- 3. How we define small, medium and large business? Is size only a preference, not a filter?

- 4. Brief says category is optional, but I made it required. Is this okay?

- 5.  Cards should come in ready order or nearest first?