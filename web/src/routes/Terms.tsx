import { Link } from "react-router-dom";
import { ContentPage } from "../components/ContentPage";

const UPDATED = "4 June 2026";
// TODO(site owner): set these before publishing.
const CONTACT = "[your contact email]";
const JURISDICTION = "[your country/state]";

export function Terms() {
  return (
    <ContentPage
      title="Terms & Conditions"
      updated={UPDATED}
      lead="Please read these terms before using the site. By using it, you agree to them."
    >
      <p>
        These Terms &amp; Conditions ("Terms") govern your access to and use of this website and its
        content (together, the "Site"). The Site is operated by its individual creator (the
        "Operator", "we", "us"). By accessing or using the Site, you ("you") agree to be bound by
        these Terms. If you do not agree, do not use the Site.
      </p>

      <h2>1. Educational and entertainment purpose only</h2>
      <p>
        The Site is provided strictly for <strong>educational, informational, and entertainment
        purposes</strong>. It presents the output of a statistical model and simulation of football
        matches. It is a demonstration of data science and software engineering, nothing more.
      </p>

      <h2>2. Not advice</h2>
      <p>
        Nothing on the Site constitutes, and it must not be relied upon as,{" "}
        <strong>betting, gambling, wagering, financial, investment, accounting, legal, tax, or any
        other professional advice</strong>, nor a recommendation, inducement, solicitation, or offer
        to place any bet, wager, or transaction. The probabilities shown are model estimates only.
        Any decision you make — including any decision to gamble — is made solely by you, at your own
        discretion and risk. You should obtain independent professional advice before acting on any
        information you find here.
      </p>

      <h2>3. No guarantee of accuracy</h2>
      <p>
        The Site's outputs are probabilistic estimates produced by a model fit to historical data.
        They are uncertain by nature, may be wrong, may contain errors or bugs, may rely on
        third-party data that is incomplete or inaccurate, and may be based on provisional
        assumptions (see the <Link to="/faq">FAQ</Link>). A single tournament cannot confirm or
        refute a probability. We make <strong>no representation or warranty</strong> that any output
        is accurate, complete, current, or reliable.
      </p>

      <h2>4. Provided "as is"</h2>
      <p>
        The Site is provided <strong>"as is" and "as available", without warranties of any kind</strong>,
        whether express, implied, or statutory, including (without limitation) implied warranties of
        merchantability, fitness for a particular purpose, accuracy, and non-infringement, to the
        fullest extent permitted by applicable law.
      </p>

      <h2>5. Limitation of liability</h2>
      <p>
        To the maximum extent permitted by applicable law, the Operator shall{" "}
        <strong>not be liable for any loss or damage</strong> of any kind — including direct,
        indirect, incidental, consequential, special, exemplary, or punitive damages, and including
        any loss of money, profits, data, goodwill, or any losses arising from gambling or financial
        decisions — arising out of or in connection with your use of, or inability to use, the Site
        or its content, whether based in contract, tort (including negligence), strict liability, or
        otherwise, even if advised of the possibility of such damages. Where liability cannot be
        excluded by law, it is limited to the maximum extent permitted.
      </p>

      <h2>6. Indemnification</h2>
      <p>
        You agree to <strong>indemnify, defend, and hold harmless</strong> the Operator and any
        contributors from and against any and all claims, liabilities, damages, losses, costs, and
        expenses (including reasonable legal fees) arising out of or related to your use or misuse of
        the Site, your reliance on its content, your violation of these Terms, or your violation of
        any law or the rights of any third party.
      </p>

      <h2>7. Responsible gambling</h2>
      <p>
        The Site does not facilitate or encourage gambling. Gambling may be illegal where you live
        and carries real financial risk; you are solely responsible for complying with the laws of
        your jurisdiction and must be of legal age. If gambling is affecting you or someone you know,
        please seek help from a qualified support organisation in your country.
      </p>

      <h2>8. No affiliation; intellectual property</h2>
      <p>
        The Site is an independent project and is <strong>not affiliated with, endorsed by, or
        sponsored by</strong> FIFA, any football association, broadcaster, betting company, or any
        national team. All team names, competition names, and related trademarks are the property of
        their respective owners and are used for identification and descriptive purposes only. The
        Site's source code is released under the MIT License; underlying match data is provided by a
        third party under its own (CC BY-NC-SA) licence and remains subject to that licence.
      </p>

      <h2>9. Third-party links and data</h2>
      <p>
        The Site may reference third-party data sources and links. We do not control and are not
        responsible for the content, accuracy, or practices of any third party.
      </p>

      <h2>10. Changes</h2>
      <p>
        We may modify the Site or these Terms at any time without notice. Changes take effect when
        posted; the "last updated" date above will reflect the latest version. Your continued use of
        the Site constitutes acceptance of the current Terms.
      </p>

      <h2>11. Governing law</h2>
      <p>
        These Terms are governed by the laws of {JURISDICTION}, without regard to its conflict-of-law
        rules. If any provision is found unenforceable, the remaining provisions remain in full
        effect.
      </p>

      <h2>12. Contact</h2>
      <p>
        Questions about these Terms can be sent to {CONTACT}. See also our{" "}
        <Link to="/privacy">Privacy Policy</Link>.
      </p>
    </ContentPage>
  );
}
