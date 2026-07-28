import { useState } from 'react';
import {
  Search,
  Book,
  MessageSquare,
  Video,
  Terminal,
  FileText,
  Zap,
  ArrowRight,
  ChevronRight
} from 'lucide-react';

const CategoryCard = ({ title, description, icon: Icon, count }) => (
  <div className="card help-category-card glass-effect animate-in">
    <div className="category-icon-bg">
      <Icon size={24} />
    </div>
    <div className="category-content">
      <h3>{title}</h3>
      <p>{description}</p>
      <span className="article-count">{count} Articles</span>
    </div>
    <ChevronRight size={20} className="category-arrow" />
  </div>
);

const HelpCenter = () => {
  const [searchQuery, setSearchQuery] = useState('');

  const categories = [
    {
      title: 'Getting Started',
      description: 'Learn the basics and set up your first integration.',
      icon: Zap,
      count: 12
    },
    {
      title: 'Integrations',
      description: 'Detailed guides for Gmail, Slack, and other platforms.',
      icon: Terminal,
      count: 24
    },
    {
      title: 'AI Priority Scoring',
      description: 'How our algorithm works and how to tune it.',
      icon: FileText,
      count: 8
    },
    {
      title: 'Team Collaboration',
      description: 'Using shared feeds and delegating tasks.',
      icon: Book,
      count: 15
    },
    {
      title: 'Video Tutorials',
      description: 'Step-by-step visual guides to mastery.',
      icon: Video,
      count: 10
    },
    {
      title: 'API & Developers',
      description: 'Build custom tools on top of Clutsch.',
      icon: Terminal,
      count: 20
    }
  ];

  const featuredArticles = [
    'How to connect your enterprise Slack workspace',
    'Fine-tuning your "Stakeholders" list for better AI scores',
    'Understanding the "Time to Action" metric',
    'Best practices for shared team feeds'
  ];

  return (
    <div className="help-center-container">
      <header className="help-hero">
        <div className="hero-content animate-in">
          <h1>How can we help?</h1>
          <p>Search our documentation or browse categories below.</p>
          <div className="help-search glass">
            <Search size={20} />
            <input 
              type="text" 
              placeholder="Search for articles, guides, or keywords..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="popular-tags">
            <span>Popular:</span>
            <button className="tag">SSO Setup</button>
            <button className="tag">Gmail Sync</button>
            <button className="tag">AI Tuning</button>
          </div>
        </div>
      </header>

      <section className="help-content-section">
        <div className="section-header">
          <h2>Browse by Category</h2>
          <button className="btn-text">View All <ArrowRight size={16} /></button>
        </div>
        <div className="category-grid">
          {categories.map((cat, i) => (
            <CategoryCard key={i} {...cat} />
          ))}
        </div>

        <div className="help-footer-grid">
          <div className="card glass-effect featured-articles">
            <h3>Featured Articles</h3>
            <ul className="article-list">
              {featuredArticles.map((article, i) => (
                <li key={i}>
                  <FileText size={18} />
                  <span>{article}</span>
                  <ChevronRight size={16} />
                </li>
              ))}
            </ul>
          </div>

          <div className="card glass-effect contact-support">
            <div className="support-icon-bg">
              <MessageSquare size={32} />
            </div>
            <h3>Still need help?</h3>
            <p>Our support team is available 24/7 for Enterprise customers.</p>
            <div className="support-actions">
              <button className="btn btn-primary">Chat with us</button>
              <button className="btn btn-secondary">Email Support</button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HelpCenter;
