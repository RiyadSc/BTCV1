import Link from 'next/link'

export default function TermsPage() {
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
          <h1 className="text-3xl font-bold text-gray-900 mb-8">TERMS OF SERVICE</h1>
          
          <div className="prose prose-gray max-w-none">
            <p className="text-gray-600 mb-6">
              <strong>Effective Date:</strong> August 26, 2025<br />
              <strong>Company:</strong> QuantREX, a Massachusetts entity ("Company," "we," "us," "our").<br />
              <strong>Services:</strong> The Company provides a software platform that delivers market analysis and/or trade signal information and, if explicitly enabled by you, transmits instructions to third-party brokers/exchanges via your API keys (collectively, the "Services").
            </p>
            
            <p className="text-gray-700 mb-6">
              By creating an account, accessing, or using the Services, you agree to these Terms of Service ("Terms"). If you do not agree, do not use the Services.
            </p>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">1. Eligibility; Compliance; Sanctions</h2>
              <p className="text-gray-700 mb-4">
                <strong>1.1 Age & capacity.</strong> You represent that you are at least 18 years old (or the age of majority where you reside) and have legal capacity to enter these Terms.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>1.2 Jurisdiction.</strong> You may use the Services only in jurisdictions where such use is lawful. You are solely responsible for complying with applicable laws, including securities, derivatives, commodities, data protection, and tax laws.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>1.3 Sanctions.</strong> You represent that you are not located in, organized under the laws of, or ordinarily resident in any embargoed/sanctioned country or on any restricted party list (e.g., OFAC). We may deny or terminate access for compliance reasons at any time.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">2. Nature of Services; No Investment Advice; No Fiduciary Duty</h2>
              <p className="text-gray-700 mb-4">
                <strong>2.1 Informational only.</strong> The Services (including signals, dashboards, analytics, research, and communications) are for informational and educational purposes only. We do not provide investment, legal, tax, accounting, or financial advice, and do not recommend any security, cryptoasset, instrument, strategy, or transaction.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>2.2 No advisor/CTA/broker.</strong> We are not a broker, dealer, investment adviser, commodity trading advisor, commodity pool operator, or money transmitter, and we do not custody funds or assets.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>2.3 Independent judgment.</strong> You make all trading decisions and bear all risk. You are solely responsible for evaluating information, configuring risk, and determining suitability.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>2.4 No fiduciary duty.</strong> We owe you no fiduciary duties. You agree that any relationship is strictly that of independent contractors.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">3. Auto-Execution; API Keys; Third-Party Integrations</h2>
              <p className="text-gray-700 mb-4">
                <strong>3.1 Optional auto-execution.</strong> If you enable auto-execution, you authorize the Services to submit trade instructions to your connected broker/exchange using your API keys according to your chosen settings. You can disable auto-execution at any time; disabling may not cancel instructions already sent.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>3.2 Your keys, your risk.</strong> You are solely responsible for safeguarding API keys, permissions, and limits. We recommend using trading-only keys with withdrawal disabled.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>3.3 No control over third parties.</strong> We do not control brokers/exchanges, their APIs, liquidity, pricing, fees, outages, or fills. We are not liable for third-party actions, delays, outages, slippage, partial fills, margin calls, liquidations, or errors.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>3.4 Execution differences.</strong> Backtests, paper trading, and live results may differ significantly due to latency, liquidity, fees, funding, or routing.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">4. Extreme Risk Disclosure (Read Carefully)</h2>
              <p className="text-gray-700 mb-4">
                Trading digital assets, derivatives, and leveraged products is high risk and may result in total loss. By using the Services, you acknowledge risks including but not limited to: market volatility; liquidity failures; adverse regulation; technology or API failures; exchange hacks or insolvency; funding rate changes; liquidation; slippage; front-running; oracle failure; bad ticks; network congestion; force majeure. <strong>HYPOTHETICAL, BACKTESTED, OR SIMULATED PERFORMANCE IS INHERENTLY LIMITED AND DOES NOT REFLECT REAL TRADING; PAST PERFORMANCE DOES NOT GUARANTEE FUTURE RESULTS.</strong>
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">5. Accounts; Security; Acceptable Use</h2>
              <p className="text-gray-700 mb-4">
                <strong>5.1 Account security.</strong> You are responsible for all activities under your account and for maintaining the confidentiality of credentials and devices. Notify us immediately of any suspected compromise.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>5.2 Acceptable use.</strong> You will not: (a) violate laws; (b) copy, scrape, or harvest the Services or signals; (c) reverse engineer, decompile, or attempt to access source code; (d) interfere with security or integrity; (e) resell, redistribute, sublicense, or white-label signals without written consent; (f) use the Services to build a competing product; (g) share your seat or credentials; (h) misrepresent performance.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>5.3 One seat per user.</strong> Accounts are personal and non-transferable. We may watermark or fingerprint outputs to trace unauthorized distribution.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">6. Subscriptions; Fees; Refunds; Chargebacks</h2>
              <p className="text-gray-700 mb-4">
                <strong>6.1 Billing.</strong> Paid plans renew automatically until canceled. You authorize us (or our processor) to charge your payment method for the then-current fees and taxes.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>6.2 No refunds.</strong> All fees are non-refundable unless required by law or expressly stated otherwise. Prorations are not provided.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>6.3 Chargebacks.</strong> Filing a chargeback or payment dispute without valid basis is a material breach. We may suspend/terminate your account, block future access, and refer the matter to collections.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>6.4 Price changes.</strong> We may modify fees upon notice effective on the next renewal term.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">7. Intellectual Property; License</h2>
              <p className="text-gray-700 mb-4">
                <strong>7.1 Ownership.</strong> We and our licensors own all rights in the Services, including software, models, signals, designs, and content.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>7.2 License to you.</strong> Subject to these Terms and payment of fees, we grant you a limited, revocable, non-exclusive, non-transferable license to access and use the Services for your personal or internal business purposes.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>7.3 Restrictions.</strong> Except as expressly permitted, you will not reproduce, distribute, publicly display, publish, or create derivative works of the Services or any signals.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>7.4 Feedback.</strong> Suggestions and feedback become our property without obligation or attribution.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">8. Confidentiality</h2>
              <p className="text-gray-700 mb-4">
                <strong>8.1 Confidential Signals.</strong> Signals, model outputs, and private materials are Company Confidential Information. You will not disclose, publish, or share them with third parties (including social media, groups, or newsletters) without our prior written consent.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>8.2 Injunctive relief.</strong> Unauthorized use or disclosure causes irreparable harm. We may seek immediate injunctive relief in addition to other remedies.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">9. Service Availability; Changes; Beta</h2>
              <p className="text-gray-700 mb-4">
                <strong>9.1 No uptime guarantee.</strong> The Services may be unavailable due to maintenance, upgrades, provider outages, or events beyond our control.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>9.2 Modifications.</strong> We may alter or discontinue features, models, or integrations at any time.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>9.3 Beta features.</strong> Beta or experimental features are provided "as is," at your own risk.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">10. Privacy; Data</h2>
              <p className="text-gray-700 mb-4">
                <strong>10.1 Privacy.</strong> Our collection and use of personal data is described in our Privacy Policy (incorporated by reference).
              </p>
              <p className="text-gray-700 mb-4">
                <strong>10.2 Telemetry.</strong> You grant us a worldwide, royalty-free license to collect and use anonymized or aggregated usage data for operating, improving, and securing the Services.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">11. Disclaimers</h2>
              <p className="text-gray-700 mb-4">
                <strong>THE SERVICES ARE PROVIDED "AS IS" AND "AS AVAILABLE." TO THE MAXIMUM EXTENT PERMITTED BY LAW, WE DISCLAIM ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, ACCURACY, NON-INFRINGEMENT, AND THAT THE SERVICES WILL BE UNINTERRUPTED, ERROR-FREE, OR PROFITABLE. WE DO NOT WARRANT ANY PARTICULAR OUTCOME, FILL, EXECUTION, OR PERFORMANCE.</strong>
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">12. Limitation of Liability</h2>
              <p className="text-gray-700 mb-4">
                <strong>TO THE MAXIMUM EXTENT PERMITTED BY LAW, IN NO EVENT SHALL COMPANY, ITS AFFILIATES, LICENSORS, OR PROVIDERS BE LIABLE FOR INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, EXEMPLARY, OR PUNITIVE DAMAGES, OR FOR LOST PROFITS, LOST REVENUE, LOST DATA, GOODWILL, OR BUSINESS INTERRUPTION, EVEN IF ADVISED OF THE POSSIBILITY.</strong>
              </p>
              <p className="text-gray-700 mb-4">
                <strong>OUR TOTAL CUMULATIVE LIABILITY FOR ANY CLAIMS ARISING OUT OF OR RELATED TO THE SERVICES SHALL NOT EXCEED THE AMOUNTS YOU PAID TO COMPANY IN THE TWELVE (12) MONTHS PRECEDING THE EVENT GIVING RISE TO LIABILITY.</strong>
              </p>
              <p className="text-gray-700 mb-4">
                Some jurisdictions do not allow certain limitations; in such cases, liability is limited to the maximum extent permitted.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">13. Indemnification</h2>
              <p className="text-gray-700 mb-4">
                You will defend, indemnify, and hold harmless Company and its officers, directors, employees, and agents from and against any claims, damages, liabilities, costs, and expenses (including reasonable attorneys' fees) arising out of or related to: (a) your use of the Services; (b) your trades or strategies; (c) breach of these Terms; (d) violation of law; or (e) disputes with third parties (including brokers/exchanges).
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">14. Term; Suspension; Termination</h2>
              <p className="text-gray-700 mb-4">
                <strong>14.1 Term.</strong> These Terms remain in effect while you use the Services.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>14.2 Suspension/Termination.</strong> We may suspend or terminate access immediately for any violation, suspected fraud/abuse, legal risk, non-payment, or at our convenience with notice (with a prorated refund only if termination is solely for our convenience).
              </p>
              <p className="text-gray-700 mb-4">
                <strong>14.3 Effect.</strong> Upon termination, your license ends and you must cease use. Sections intended to survive (including 2–5, 7–13, 14.3, 15–18) survive termination.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">15. Disputes; Binding Arbitration; Class Action Waiver</h2>
              <p className="text-gray-700 mb-4">
                <strong>PLEASE READ THIS SECTION CAREFULLY. IT AFFECTS YOUR LEGAL RIGHTS.</strong>
              </p>
              <p className="text-gray-700 mb-4">
                <strong>15.1 Arbitration agreement.</strong> Any dispute, claim, or controversy arising out of or relating to these Terms or the Services shall be resolved by binding arbitration administered by JAMS under its Commercial Rules. The seat of arbitration is Boston, Massachusetts, and the language is English. The arbitrator's award may be entered in any court of competent jurisdiction.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>15.2 Individual claims only.</strong> <strong>YOU AND COMPANY WAIVE ANY RIGHT TO A JURY TRIAL AND TO PARTICIPATE IN A CLASS, COLLECTIVE, OR REPRESENTATIVE ACTION.</strong>
              </p>
              <p className="text-gray-700 mb-4">
                <strong>15.3 Injunctive relief.</strong> Notwithstanding the foregoing, either party may seek provisional or injunctive relief in any court of competent jurisdiction to protect Confidential Information or IP.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>15.4 Opt-out.</strong> You may opt out of arbitration within 30 days of first acceptance by sending written notice to legal@quantsignalpro.com with subject "Arbitration Opt-Out."
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">16. Governing Law; Venue</h2>
              <p className="text-gray-700 mb-4">
                These Terms are governed by the laws of Massachusetts, without regard to conflict-of-laws rules, except to the extent preempted by federal law. Subject to Section 15, exclusive venue for any permitted court action is the state or federal courts located in Suffolk County, Massachusetts, and you consent to personal jurisdiction there.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">17. Export; Anti-Corruption</h2>
              <p className="text-gray-700 mb-4">
                You agree to comply with all applicable export control and anti-corruption/anti-bribery laws (including the U.S. FCPA and UK Bribery Act). You will not export or re-export the Services in violation of law.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">18. Miscellaneous</h2>
              <p className="text-gray-700 mb-4">
                <strong>18.1 Entire agreement.</strong> These Terms (plus any order form and Privacy Policy) are the entire agreement and supersede prior or contemporaneous agreements.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>18.2 Amendments.</strong> We may update these Terms by posting the revised version with a new Effective Date. Continued use constitutes acceptance. Material changes will be notified.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>18.3 Assignment.</strong> You may not assign or transfer these Terms without our prior written consent. We may assign freely.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>18.4 Severability.</strong> If any provision is held invalid, the remainder remains in effect.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>18.5 No waiver.</strong> Failure to enforce a provision is not a waiver.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>18.6 Force majeure.</strong> We are not liable for delays or failures caused by events beyond our reasonable control (e.g., Internet failures, power outages, DDoS, wars, disasters, regulatory actions).
              </p>
              <p className="text-gray-700 mb-4">
                <strong>18.7 Notices.</strong> We may provide notices via the Services, email, or your account. You must send legal notices to: legal@quantsignalpro.com and avxngardmedia@gmail.com.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">19. Strategy-Specific Disclosures (Model Behavior)</h2>
              <p className="text-gray-700 mb-4">
                <strong>19.1 Adaptive exits.</strong> Where the model uses adaptive entries/exits (not fixed TP/SL), you acknowledge that exits may be discretionary or algorithmic and may differ from traditional retail stops, potentially increasing drawdown or duration.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>19.2 Latency & divergence.</strong> Signals may appear simultaneously to many users; execution timing, fees, and slippage will vary, causing materially different outcomes.
              </p>
              <p className="text-gray-700 mb-4">
                <strong>19.3 Hypothetical performance.</strong> Any presented equity curves, win rates, or PnL are hypothetical unless explicitly labeled as live, audited, and net of fees and slippage. Hypothetical results are subject to hindsight bias and model overfitting.
              </p>
            </section>
            
            <section className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">20. Contact</h2>
              <p className="text-gray-700 mb-4">
                Questions? avxngardmedia@gmail.com
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}

