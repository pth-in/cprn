const { useState, useEffect, useCallback, useRef } = React;

const SUPABASE_URL = "https://tvbmjectzcowsjzidumg.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_NFMG2axuLqnH2AbPUjR7OA_L70ojzSM";

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const App = () => {
    const [incidents, setIncidents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedIncident, setSelectedIncident] = useState(null);
    const [initialSync, setInitialSync] = useState(false);
    const [theme, setTheme] = useState(localStorage.getItem('cprn-theme') || 'light');

    const PAGE_SIZE = 12;

    // --- Helper: Strip HTML ---
    const stripHtml = (html) => {
        let doc = new Error().stack ? new DOMParser().parseFromString(html, 'text/html') : null;
        return doc ? doc.body.textContent || "" : html.replace(/<[^>]*>?/gm, '');
    };

    // --- Theme Toggle ---
    useEffect(() => {
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('cprn-theme', theme);
    }, [theme]);

    const toggleTheme = () => setTheme(prev => prev === 'light' ? 'dark' : 'light');

    // --- Supabase Interaction ---
    const fetchIncidents = useCallback(async (isNewSearch = false) => {
        setLoading(true);
        const start = isNewSearch ? 0 : page * PAGE_SIZE;
        const end = start + PAGE_SIZE - 1;

        let query = supabaseClient
            .from('incidents')
            .select('*', { count: 'exact' })
            .order('incident_date', { ascending: false })
            .range(start, end);

        if (searchQuery) {
            query = query.or(`title.ilike.%${searchQuery}%,description.ilike.%${searchQuery}%,location_raw.ilike.%${searchQuery}%`);
        }

        const { data, error, count } = await query;

        if (error) {
            console.error("Fetch Error:", error);
        } else {
            setIncidents(prev => isNewSearch ? data : [...prev, ...data]);
            setHasMore(incidents.length + data.length < (count || 0));
            setInitialSync(true);
        }
        setLoading(false);
    }, [page, searchQuery]);

    useEffect(() => {
        fetchIncidents(true);
    }, [searchQuery]);

    useEffect(() => {
        if (page > 0) fetchIncidents();
    }, [page]);

    // Intersection Observer for Infinite Scroll
    const observer = useRef();
    const lastIncidentRef = useCallback(node => {
        if (loading) return;
        if (observer.current) observer.current.disconnect();
        observer.current = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && hasMore) {
                setPage(prev => prev + 1);
            }
        });
        if (node) observer.current.observe(node);
    }, [loading, hasMore]);

    // Format Date
    const formatDate = (dateStr) => {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    };

    if (!initialSync) {
        return (
            <div className="initial-loader">
                <div className="spinner"></div>
                <p>Loading CPRN Mission Control...</p>
            </div>
        );
    }

    return (
        <div className="app-container">
            <header className="main-header">
                <div className="logo">
                    <span className="logo-text">CPRN<span className="logo-accent">.</span></span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                    <div className="stats" style={{ fontSize: '0.8rem', opacity: 0.6 }}>
                        {incidents.length} Reports Found
                    </div>
                    <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle Theme">
                        <i data-lucide={theme === 'light' ? "moon" : "sun"}></i>
                    </button>
                </div>
            </header>

            <div className="search-wrapper">
                <i data-lucide="search" className="search-icon"></i>
                <input
                    type="text"
                    className="search-input"
                    placeholder="Search incidents or locations..."
                    value={searchQuery}
                    onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setPage(0);
                    }}
                />
            </div>

            <main className="incident-grid">
                {incidents.map((incident, index) => {
                    const isLast = incidents.length === index + 1;
                    const cleanDesc = stripHtml(incident.description);

                    return (
                        <div key={incident.id} className="card" ref={isLast ? lastIncidentRef : null}>
                            <div className="card-header">
                                <span className="date-badge">{formatDate(incident.incident_date)}</span>
                                <div className="source-badges">
                                    {incident.sources.map((s, i) => (
                                        <span key={i} className="badge">{s.name}</span>
                                    ))}
                                </div>
                            </div>

                            <h2 className="card-title">{incident.title}</h2>

                            <div className="location-tag">
                                <i data-lucide="map-pin" className="location-icon"></i>
                                {incident.location_raw}
                            </div>

                            <p className="card-description">{cleanDesc}</p>

                            <div className="card-footer">
                                <button className="btn-read-more" onClick={() => setSelectedIncident(incident)}>
                                    Details & Analysis
                                </button>
                            </div>
                        </div>
                    );
                })}
            </main>

            {loading && (
                <div className="scroll-trigger">
                    <div className="spinner" style={{ margin: '0 auto' }}></div>
                </div>
            )}

            {!hasMore && incidents.length > 0 && (
                <div className="scroll-trigger">
                    <p style={{ opacity: 0.5, fontSize: '0.9rem' }}>No further reports found.</p>
                </div>
            )}

            {/* Modal */}
            {selectedIncident && (
                <div className="modal-overlay" onClick={() => setSelectedIncident(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <div style={{ marginBottom: '2rem' }}>
                            <div className="date-badge" style={{ marginBottom: '0.5rem' }}>{formatDate(selectedIncident.incident_date)}</div>
                            <h1 className="card-title" style={{ fontSize: '1.8rem', marginBottom: '1rem' }}>{selectedIncident.title}</h1>
                            <div className="location-tag" style={{ fontSize: '1rem' }}>
                                <i data-lucide="map-pin" className="location-icon"></i> {selectedIncident.location_raw}
                            </div>
                        </div>

                        <div style={{ lineHeight: 1.8 }}>
                            <p style={{ whiteSpace: 'pre-wrap', marginBottom: '2rem' }}>
                                {stripHtml(selectedIncident.description)}
                            </p>

                            <h4 style={{ marginBottom: '1rem', color: 'var(--accent-gold)' }}>Verified Reporting Sources:</h4>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                                {selectedIncident.sources.map((s, i) => (
                                    <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="badge" style={{ display: 'block', padding: '1rem', textAlign: 'left', textDecoration: 'none' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span>Access Original Report from <strong>{s.name}</strong></span>
                                            <i data-lucide="external-link" style={{ width: '16px' }}></i>
                                        </div>
                                    </a>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);

// Refresh Icons
setInterval(() => {
    if (window.lucide) window.lucide.createIcons();
}, 200);
