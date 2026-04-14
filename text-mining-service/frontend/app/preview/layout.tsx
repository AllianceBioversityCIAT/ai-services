import '@/styles/star-mock.css';
import '@/styles/bulk-upload.css';

export default function PreviewLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {/* Top Navigation */}
      <nav className="star-topnav">
        <div className="star-nav-container">
          <div className="star-nav-left">
            <div className="star-logo">🌟STAR</div>
            <div className="star-nav-links">
              <a href="#" className="star-nav-link">Home</a>
              <a href="#" className="star-nav-link star-nav-link-active">Bulk Upload</a>
            </div>
          </div>
        </div>
      </nav>

      <div className="star-container">
        {/* Sidebar */}
        <aside className="star-sidebar"></aside>

        {/* Main Content */}
        <main className="star-main-content">
          <div className="star-breadcrumb">
            <span>Center admin</span>
            <span className="star-breadcrumb-separator">{'>'}</span>
            <span className="star-breadcrumb-current">Bulk upload</span>
          </div>

          <div className="star-embedded-content">
            {children}
          </div>
        </main>
      </div>
    </>
  );
}
