## 1. System Architecture

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