# CPRN: Brainstorming & Strategic Plan (India Focus)

This document outlines the strategic plan for the **Christian Persecution Response Network (CPRN)**, now specifically focused on monitoring and responding to incidents within **India**.

## 1. Information Gathering (Data Ingestion)

To effectively respond, we need reliable, real-time information from multiple sources.

### Priority 1: Automated RSS Ingestion (Easily Integrated)
- **International Christian Concern (ICC)**: [persecution.org/feed](https://www.persecution.org/feed)
- **Morning Star News**: [morningstarnews.org/feed](https://morningstarnews.org/tag/religious-persecution/feed/)
- **Christian Today India**: [christiantoday.co.in/rss.xml](https://www.christiantoday.co.in/rss.xml)
- [PENDING] **UCA News**: `ucanews.com/rss/news` (Needs "India" + Keyword filtering)
- [PENDING] **AsiaNews**: `asianews.it/index.php?l=en&art=1&size=0` (Needs "India" filtering)

### Priority 2: NGO & Report Scraping (Targeted)
These sources provide deeper, verified reports but often lack traditional RSS feeds:
- **Evangelical Fellowship of India (EFI-RLC)**: High-quality verified reports from `efionline.org`. Requires a custom scraper for their "News" or "Reports" page.
- **United Christian Forum (UCF)**: Critical human rights data from Delhi. 
- **FIACONA**: Gather ground intelligence for US/International advocacy.

### Deduplication Strategy: "One Incident, Many Sources"
To avoid cluttering the feed when multiple sources report the same event:
- **Similarity Comparison**: The ingestion script compares incoming titles with DB entries from the last 3 days.
- **Source Grouping**: If a match is found, the new source is added to the existing card. 
- **Benefits**:
    - Cleaner UI (No duplicate cards).
    - Higher Credibility (Shows multiple sources for one event).
    - Richer Data (Combined descriptions).

### Priority 3: Social Media Sentinels (Zero-Cost Proactive Monitoring)
To catch incidents before they hit the major news wires, we monitor high-frequency "Sentinel" accounts on X (Twitter) and Facebook:
- **X Sentinels**: `@UCF_India`, `@persecution_in` (Persecution Relief), `@EFI_India`, `@ADFIndia`.
- **Facebook Sentinels**: `United Christian Forum (UCF)`, `Evangelical Fellowship of India`.
- **Implementation**: Instead of the paid X API, we use RSS-proxies (Nitter/RSS-Bridge) to convert these timelines into automated data streams.

### Priority 4: Local Networks & Crowdsourcing
- **Direct Submissions**: A future secure form for verified partners to submit reports.
- **VPN & Encrypted Tools**: Providing tools and training for those in high-risk areas to communicate safely.

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

### Component Breakdown: "The Incident Card"
Each card should be a high-impact visual summary:
- **Header**: Incident Date + Source Badges (e.g., [ICC] [Morning Star]).
- **Body**: 
    - Bold Title (max 2 lines).
    - Location Tag (e.g., "📍 Ludhiana, Punjab").
    - Short truncated description (max 3 lines).
- **Footer**: 
    - "Read More" button.
    - Social Share Icon (WhatsApp/X).
    - Status Badge (e.g., "Verified" or "Active").

### Detail Modal / Page
When a user clicks "Read More":
- **Full Narrative**: The complete text from the sources.
- **Source Links**: Clickable list of original reports.
- **Action Dashboard**: 
    - Permanent "GiveSendGo" button (if available).
    - Prayer Points (specific needs like "Pray for the family").
    - Legal Status tracker.

### Aesthetics & "Vibe"
- **Color Palette**: 
    - Deep Charcoal/Slate Background (Serious, trustworthy feel).
    - Accent: Warm Gold or Crimson (Urgency without being overwhelming).
- **Typography**: Clean sans-serif (Inter or Montserrat) for high legibility.
- **Micro-Animations**: Subtle hover effects on cards and a "smooth load" effect for infinite scroll.

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
