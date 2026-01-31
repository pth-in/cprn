# CPRN: Brainstorming & Strategic Plan

This document outlines the initial brainstorming for the **Christian Persecution Response Network (CPRN)**. The goal is to build a robust system for gathering information on persecution and reaching out to provide support.

## 1. Information Gathering (Data Ingestion)

To effectively respond, we need reliable, real-time information from multiple sources.

### Priority 1: Automated RSS Ingestion (Easily Integrated)
- **International Christian Concern (ICC)**: [persecution.org/feed](https://www.persecution.org/feed)
    - *Coverage*: Global, rapid reporting on incidents.
- **Morning Star News**: [morningstarnews.org/feed](https://morningstarnews.org/tag/religious-persecution/feed/)
    - *Coverage*: In-depth investigative journalism on persecution.

### Priority 2: Semi-Automated Monitoring (Periodic Scraping)
- **Voice of the Martyrs (VOM)**: Monitoring [persecution.com](https://www.persecution.com/newsroom/) and their podcast feed.
- **Open Doors (World Watch List)**: Annual data ingestion from leur dossiers and weekly prayer updates.

### Priority 3: Local Networks & Crowdsourcing
- **Direct Submissions**: A future secure form for verified partners to submit reports.
- **Social Media Sentinel**: Monitoring specific hashtags or accounts (requires careful filtering).

---

## 2. Outreach & Response Strategy

Once information is verified, the network must act swiftly but safely.

### Secure Communication Channels
- **First Response**: Using Signal or Telegram for immediate, end-to-end encrypted communication with people in danger.
- **Safe Houses & Logistics**: Coordinated through secure, non-centralized channels to avoid surveillance.
- **VPN & Encrypted Tools**: Providing tools and training for those in high-risk areas to communicate safely.

### Verification Process
- **Truth over Haste**: Implementing a multi-factor verification system (local contacts, photo/video evidence, cross-referencing news) to ensure resources are directed correctly and to maintain credibility.

### Local Volunteer Network
- **Regional Chapters**: Establishing small, decentralized cells of volunteers who can provide physical presence, food, medicine, or legal aid locally.
- **Training**: Providing guidelines on non-violent response, legal rights, and emotional support.

---

## 3. Product Vision: The CPRN Incident Portal

The portal will be the public face of the network, designed for high impact and easy sharing.

### UI/UX: The "Incident Stream"
- **Infinite Scroll Landing Page**: A continuous feed of incident cards, sorted by `Incident Date` (newest first).
- **Responsive Card Layout**:
    - **Mobile**: 1 card per row (stacking vertically).
    - **Tablet/Desktop**: Responsive grid (2-4 cards per row depending on width).
- **Filtering & Search**:
    - Real-time search by location (Country/City), names, or description keywords.
    - Tag-based filtering (e.g., "Legal Aid Needed", "Evicted").
- **Individual Incident Pages**:
    - Direct links for every card (e.g., `cprn.org/incident/123`).
    - Detailed narrative, links to original news sources, and a dedicated **Action Section** (e.g., GiveSendGo links).

---

## 4. Finalized Tech Stack ($0 Budget)

To guarantee **$0.00** operational cost while maintaining high performance, we will use:

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Frontend** | **Vite + React** | Lightweight, modern, and high performance. |
| **Backend/DB**| **Supabase (Free)**| **Choice: Supabase.** Relational PostgreSQL is better for filtering/sorting by location and date than NoSQL options. |
| **Hosting** | **GitHub Pages** | Permanent free hosting for static sites. |
| **Pagination** | **Infinite Scroll** | Data will be fetched in paginated chunks (e.g., 20 items) to minimize API load and maximize speed. |
| **Automation** | **GitHub Actions** | **The Engine.** Periodically runs the ingestion script for $0 cost. |

### Ingestion Details
- **Frequency**: **Every 12 hours**. This keeps the data fresh without being aggressive.
- **Language**: Python (best-in-class libraries for RSS and data cleanup).
- **Storage**: Supabase PostgreSQL.
- **Logic**: Intelligent "Upsert" based on the source URL (so we don't create duplicates when the script runs again).

---

## 5. Security & Privacy Policy

> [!CAUTION]
> **Data Integrity Rule**: No private, non-public, or sensitive volunteer data will ever be stored in the Supabase cloud.

- **Public Data Only**: The database will strictly contain information already available in the public domain (news reports, public NGO alerts).
- **External Links**: We will link to original sources and verified donation pages (GiveSendGo) rather than processing payments or hosting private files.
- **Volunteer Safety**: Internal communication and NGO partner coordination happen outside this public-facing portal (e.g., Signal).

---

## 6. Sample Data Schema (v1.0)

This schema will be used to structure the incidents for the card view:

```json
{
  "id": "uuid",
  "incident_date": "2026-01-30",
  "title": "Church Vandalized in Punjab",
  "location": {
    "city": "Ludhiana",
    "state": "Punjab",
    "country": "India"
  },
  "description": "Short summary of the incident based on public reports...",
  "tags": ["Vandalism", "Legal Aid Needed"],
  "source_urls": ["https://news-source.com/article/123"],
  "action_links": {
    "give_send_go": "https://givesendgo.com/cprn-help-123"
  },
  "image_url": "https://res.cloudinary.com/..."
}
```

---

## 7. Next Steps for Brainstorming

1. **Source Identification**: Which 2-3 news sources or NGOs should we prioritize for our first automated scrape?
2. **UI Look & Feel**: Should the cards be stark and clinical, or more like a visual dashboard with maps/charts?
3. **Drafting the "Help" Section**: What information is most critical on the "Details" page for someone who wants to help?
