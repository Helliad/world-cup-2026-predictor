import { Link } from "react-router-dom";
import { ContentPage } from "../components/ContentPage";

const UPDATED = "4 June 2026";
const CONTACT = "hi@abhaybagda.com";

export function Privacy() {
  return (
    <ContentPage title="Privacy Policy" updated={UPDATED} lead="The short version: this site does not collect your personal data.">
      <p>
        This website (the "Site") is a static, educational project that displays football statistics.
        It has no accounts, no logins, no forms, and no backend server of its own. This policy
        explains what does and does not happen when you visit.
      </p>

      <h2>Information we collect</h2>
      <p>
        <strong>None.</strong> We do not collect, store, sell, or share any personal information. We
        do not ask for your name, email, or any other details, and there are no contact or comment
        forms.
      </p>

      <h2>Cookies and analytics</h2>
      <p>
        The Site sets <strong>no cookies</strong> and runs <strong>no analytics or advertising
        trackers</strong>. We do not profile visitors or track you across sites.
      </p>

      <h2>What stays in your browser</h2>
      <ul>
        <li>
          Light/dark theme is an in-memory preference for the current visit only — it is not saved or
          transmitted.
        </li>
        <li>
          "What if" scenarios are encoded in the page URL so you can share them. That data lives in
          your browser's address bar and is only sent to a third party if <em>you</em> share or open
          such a link.
        </li>
      </ul>

      <h2>Third-party services</h2>
      <p>
        Like any website, when your browser loads the Site it necessarily contacts the servers that
        host and serve it, and those providers may record standard technical request logs (such as IP
        address, browser type, and time of request) under their own privacy policies, which we do not
        control:
      </p>
      <ul>
        <li>
          <strong>Hosting / CDN.</strong> The Site is served as static files by a hosting provider
          (e.g. a static-site host such as GitHub Pages), which may keep standard server logs.
        </li>
        <li>
          <strong>Web fonts.</strong> The Site may load typefaces from a third-party font provider
          (e.g. Google Fonts), which can receive your IP address when the font is requested.
        </li>
      </ul>
      <p>
        We do not receive, access, or store any of these logs. If you wish to avoid third-party font
        requests, the fonts gracefully fall back to your system fonts.
      </p>

      <h2>Children</h2>
      <p>
        The Site is general-audience and does not knowingly collect information from anyone,
        including children.
      </p>

      <h2>Changes</h2>
      <p>
        We may update this policy as the Site evolves; the "last updated" date above will change
        accordingly. Continued use of the Site after an update means you accept the revised policy.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy can be sent to{" "}
        <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. See also our{" "}
        <Link to="/terms">Terms &amp; Conditions</Link>.
      </p>
    </ContentPage>
  );
}
