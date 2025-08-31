import Link from 'next/link'

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Go back link */}
        <div className="mb-6">
          <Link href="/" className="text-blue-600 hover:text-blue-700 font-medium">
            ← Go back
          </Link>
        </div>
        
        <div className="bg-white shadow rounded-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Privacy Policy</h1>
          
          <div className="prose prose-gray max-w-none">
            <p className="text-gray-600 mb-6">
              <strong>Effective Date:</strong> August 26, 2025<br />
              <strong>Company:</strong> QuantREX ("Company," "we," "us," "our")<br />
              <strong>Contact:</strong> avxngardmedia@gmail.com
            </p>
            
            <p className="text-gray-700 mb-6">
              We value your privacy. This Privacy Policy explains how we collect, use, share, and protect information in connection with our software platform and related services (the "Services"). By accessing or using the Services, you agree to this Privacy Policy.
            </p>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">1. Information We Collect</h2>
              <p className="text-gray-700 mb-4">
                We collect the following categories of information:
              </p>
              
              <h3 className="text-lg font-semibold text-gray-900 mb-3">1.1 Account Information</h3>
              <p className="text-gray-700 mb-4">
                Name, email address, username, password, and subscription details.
              </p>
              
              <h3 className="text-lg font-semibold text-gray-900 mb-3">1.2 Payment Information</h3>
              <p className="text-gray-700 mb-4">
                Processed securely by third-party payment processors (e.g., Stripe, PayPal). We do not store credit card numbers.
              </p>
              
              <h3 className="text-lg font-semibold text-gray-900 mb-3">1.3 Usage & Device Data</h3>
              <p className="text-gray-700 mb-4">
                Log data such as IP address, browser type, device identifiers, operating system, and timestamps.
              </p>
              <p className="text-gray-700 mb-4">
                Interaction data such as clicks, navigation, error reports, and usage frequency.
              </p>
              
              <h3 className="text-lg font-semibold text-gray-900 mb-3">1.4 Trading & API Data</h3>
              <p className="text-gray-700 mb-4">
                Broker/exchange account identifiers (if you connect them).
              </p>
              <p className="text-gray-700 mb-4">
                API keys provided by you (encrypted and stored securely, with limited permissions recommended).
              </p>
              <p className="text-gray-700 mb-4">
                Trading instructions generated through our Services.
              </p>
              
              <h3 className="text-lg font-semibold text-gray-900 mb-3">1.5 Communications</h3>
              <p className="text-gray-700 mb-4">
                Emails, messages, or other communications you send us.
              </p>
              <p className="text-gray-700 mb-4">
                Support requests and related correspondence.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">2. How We Use Information</h2>
              <p className="text-gray-700 mb-4">
                We use your information to:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>Provide, operate, and improve the Services.</li>
                <li>Authenticate you and secure your account.</li>
                <li>Process payments and manage subscriptions.</li>
                <li>Deliver trade signals, analytics, and auto-execution (if enabled).</li>
                <li>Send administrative notices, updates, and marketing communications (you may opt out).</li>
                <li>Monitor system performance, detect fraud, and ensure compliance with laws.</li>
                <li>Conduct anonymized analytics and product research.</li>
              </ul>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">3. Sharing of Information</h2>
              <p className="text-gray-700 mb-4">
                We do not sell your personal data. We may share information as follows:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li><strong>Service providers:</strong> Payment processors, hosting providers, analytics tools, and support platforms.</li>
                <li><strong>Brokers/exchanges:</strong> If you enable API integrations, trade instructions may be transmitted to those third parties.</li>
                <li><strong>Legal obligations:</strong> To comply with applicable law, regulation, legal process, or government requests.</li>
                <li><strong>Business transfers:</strong> In case of merger, acquisition, financing, or sale of assets, your data may be transferred.</li>
                <li><strong>Protection of rights:</strong> To enforce our Terms, investigate fraud/abuse, or protect our property, users, or the public.</li>
              </ul>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">4. Data Retention</h2>
              <p className="text-gray-700 mb-4">
                We retain personal data only as long as necessary to provide the Services, comply with legal obligations, resolve disputes, and enforce agreements. API keys and sensitive data may be deleted immediately upon request.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">5. Security</h2>
              <p className="text-gray-700 mb-4">
                We implement technical and organizational measures to protect your data, including:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>Encrypted storage of API keys.</li>
                <li>TLS encryption in transit.</li>
                <li>Access controls and monitoring.</li>
              </ul>
              <p className="text-gray-700 mb-4">
                No system is 100% secure. You are responsible for safeguarding your credentials and API keys.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">6. Your Rights</h2>
              <p className="text-gray-700 mb-4">
                Depending on where you reside, you may have rights under data protection laws (e.g., GDPR, CCPA), including:
              </p>
              <ul className="list-disc pl-6 text-gray-700 mb-4">
                <li>Access to your data.</li>
                <li>Request correction or deletion.</li>
                <li>Restrict or object to processing.</li>
                <li>Data portability.</li>
                <li>Opt out of marketing emails.</li>
              </ul>
              <p className="text-gray-700 mb-4">
                Requests can be sent to legal@quantsignalpro.com. We will verify your identity before processing.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">7. International Users</h2>
              <p className="text-gray-700 mb-4">
                If you access the Services from outside the United States, you consent to processing and storage in the U.S. or other jurisdictions where we operate.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">8. Children's Privacy</h2>
              <p className="text-gray-700 mb-4">
                The Services are not directed to individuals under 18. We do not knowingly collect information from minors. If we become aware of such collection, we will delete the data.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">9. Changes to This Policy</h2>
              <p className="text-gray-700 mb-4">
                We may update this Privacy Policy from time to time. Updates will be posted with a new Effective Date. Material changes will be communicated via email or through the Services.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">10. Contact Us</h2>
              <p className="text-gray-700 mb-4">
                For questions or requests, contact:
              </p>
              <p className="text-gray-700 mb-4">
                📧 avxngardmedia@gmail.com
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
