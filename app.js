const { useState, useEffect, useCallback, useRef } = React;

// --- Supabase Config ---
// Since this is a static frontend on GitHub Pages, the URL and Anon Key are public.
// Replace these with your actual Supabase credentials.
const SUPABASE_URL = "https://your-project-url.supabase.co";
const SUPABASE_ANON_KEY = "your-anon-key";

const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const App = () => {
    const [incidents, setIncidents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [hasMore, setHasMore] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedIncident, setSelectedIncident] = useState(null);
    const [initialSync, setInitialSync] = useState(false);

    const PAGE_SIZE = 12;

    // Fetch Incidents from Supabase
    const fetchIncidents = useCallback(async (isNewSearch = false) => {
        setLoading(true);
        const start = isNewSearch ? 0 : page * PAGE_SIZE;
        const end = start + PAGE_SIZE - 1;

        let query = supabase
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
            setHasMore(incidents.length + data.length < count);
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

    // Infinite Scroll Observer
    const observer = useRef();
    const lastIncidentRef = useCallback(node => {
        if (loading) return;
        if (observer.current) observer.current.disconnect();
        observer.current = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && hasMore) {
                setPage(prevPage => prevPage + 1);
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
                <p>Establishing Secure Connection...</p>
            </div>
        );
    }

    return (
        <div className="app-container">
            <header className="main-header">
                <a href="#" className="logo">
                    <div className="logo-icon"><i data-lucide="shield-check"></i></div>
                    <span className="logo-text">CPRN<span className="logo-accent">.</span></span>
                </a>
                <div className="stats" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {incidents.length} Incident{incidents.length !== 1 ? 's' : ''} Documented
                </div>
            </header>

            <div className="search-wrapper">
                <i data-lucide="search" className="search-icon"></i>
                <input
                    type="text"
                    className="search-input"
                    placeholder="Search by location, names, or incident keywords..."
                    value={searchQuery}
                    onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setPage(0);
                    }}
                />
            </div>

            <main className="incident-grid">
                {incidents.map((incident, index) => {
                    const isLastElement = incidents.length === index + 1;
                    return (
                        <div
                            key={incident.id}
                            className="card"
                            ref={isLastElement ? lastIncidentRef : null}
                        >
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

                            <p className="card-description">{incident.description}</p>

                            <div className="card-footer">
                                <button className="btn-read-more" onClick={() => setSelectedIncident(incident)}>
                                    Details & Research
                                </button>
                                {incident.is_verified && (
                                    <div title="Verified Incident" style={{ color: 'var(--accent-gold)' }}>
                                        <i data-lucide="verified" style={{ width: '20px' }}></i>
                                    </div>
                                )}
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
                    <p style={{ color: 'var(--text-muted)' }}>You have reached the end of the stream.</p>
                </div>
            )}

            {/* Incident Details Modal */}
            {selectedIncident && (
                <div className="modal-overlay" onClick={() => setSelectedIncident(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <button className="close-btn" onClick={() => setSelectedIncident(null)}>
                            <i data-lucide="x"></i>
                        </button>

                        <div style={{ marginBottom: '2rem' }}>
                            <span className="date-badge" style={{ marginBottom: '1rem', display: 'inline-block' }}>
                                {formatDate(selectedIncident.incident_date)}
                            </span>
                            <h1 className="card-title" style={{ fontSize: '2rem', marginBottom: '1rem' }}>
                                {selectedIncident.title}
                            </h1>
                            <div className="location-tag" style={{ fontSize: '1rem' }}>
                                <i data-lucide="map-pin" className="location-icon" style={{ width: '18px' }}></i>
                                {selectedIncident.location_raw}
                            </div>
                        </div>

                        <div className="modal-body">
                            <h3 style={{ color: 'var(--accent-gold)', marginBottom: '1rem', size: '0.9rem', textTransform: 'uppercase' }}>Incident Narrative</h3>
                            <p style={{ whiteSpace: 'pre-wrap', marginBottom: '2rem', color: 'var(--text-primary)' }}>
                                {selectedIncident.description}
                            </p>

                            <h3 style={{ color: 'var(--accent-gold)', marginBottom: '1rem', size: '0.9rem', textTransform: 'uppercase' }}>Original Sources</h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                {selectedIncident.sources.map((s, i) => (
                                    <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="badge" style={{ display: 'block', padding: '1rem', textDecoration: 'none' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <strong>{s.name}</strong>
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

// Initialize Lucide Icons after React Renders
const render = () => {
    const root = ReactDOM.createRoot(document.getElementById('root'));
    root.render(<App />);

    // Lucide helper
    setTimeout(() => {
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }, 100);
};

render();
