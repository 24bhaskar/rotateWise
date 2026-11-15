import { NavLink, Outlet } from "react-router-dom";
import { StepHeader } from "../../components/ui";
import { useAppParams, withQuery } from "../../lib/url";

export function EvidenceLayout() {
  const { query } = useAppParams();
  const tabs = [
    { to: "/evidence", label: "How good is the model?", end: true },
    { to: "/evidence/failures", label: "Where it fails" },
    { to: "/evidence/data", label: "Data, methods & limits" },
  ];
  return (
    <div className="wrap page">
      <StepHeader step="Evidence" title="The evidence behind RotateWise"
                  lede="For judges, agronomists and anyone who wants to check our work: how the model was tested, where it breaks, and every source we used." />
      <nav className="subnav" aria-label="Evidence sections">
        {tabs.map((t) => (
          <NavLink key={t.to} to={withQuery(t.to, query)} end={t.end} className={({ isActive }) => `navlink ${isActive ? "active" : ""}`}>{t.label}</NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
