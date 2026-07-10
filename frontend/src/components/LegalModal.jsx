import React from 'react';
import { X } from 'lucide-react';
import useFocusTrap from '../hooks/useFocusTrap';

const LegalModal = ({ type, onClose }) => {
  const { containerRef, onKeyDown } = useFocusTrap(onClose, typeof isOpen === 'undefined' ? true : isOpen);
  const content = {
    tos: {
      title: "Terms of Service",
      body: (
        <>
          <h3>1. Acceptance of Terms</h3>
          <p>By accessing and using PriorityFlow, you agree to be bound by these Terms of Service. If you do not agree to these terms, please do not use our service.</p>
          
          <h3>2. Description of Service</h3>
          <p>PriorityFlow provides a unified communication dashboard that aggregates messages from various platforms and prioritizes them using AI.</p>
          
          <h3>3. User Accounts</h3>
          <p>You are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.</p>
          
          <h3>4. Privacy & Data</h3>
          <p>Your use of the service is also governed by our Privacy Policy. We process data according to GDPR and other applicable regulations.</p>
        </>
      )
    },
    privacy: {
      title: "Privacy Policy",
      body: (
        <>
          <h3>1. Data Collection</h3>
          <p>We collect information you provide directly to us, as well as data from the communication platforms you connect to PriorityFlow.</p>
          
          <h3>2. How We Use Data</h3>
          <p>We use your data to provide, maintain, and improve the service, including the AI-driven prioritization features.</p>
          
          <h3>3. Data Security</h3>
          <p>We implement robust security measures to protect your data, including encryption of sensitive credentials at rest.</p>
          
          <h3>4. Your Rights (including DPDP Compliance)</h3>
          <p>Under regulations like GDPR and India's DPDP Act, you have the following rights:</p>
          <ul>
            <li><strong>Right to Access:</strong> See what data we process.</li>
            <li><strong>Right to Correction & Erasure:</strong> Update or delete your data.</li>
            <li><strong>Right to Withdraw Consent:</strong> Stop data processing at any time.</li>
            <li><strong>Right to Nominate:</strong> (DPDP specific) Nominate an individual to exercise your rights.</li>
          </ul>

          <h3>5. Grievance Redressal</h3>
          <p>If you have any privacy concerns or grievances, please contact our Data Protection Officer:</p>
          <p><strong>Email:</strong> dpo@priorityflow.com</p>
          <p>We aim to respond to all grievances within 7 days.</p>
        </>
      )
    }
  };

  const active = content[type] || content.tos;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card legal-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{active.title}</h2>
          <button className="close-btn" onClick={onClose} aria-label="Close dialog">
            <X size={24} />
          </button>
        </div>
        <div className="modal-body">
          {active.body}
        </div>
        <div className="modal-footer">
          <button className="btn btn-primary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

export default LegalModal;
