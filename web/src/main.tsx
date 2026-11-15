import "@fontsource/fraunces/600.css";
import "@fontsource/fraunces/700.css";
import "@fontsource-variable/source-sans-3";
import "./styles/global.css";

import { lazy, StrictMode, Suspense, type ComponentType } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Loading } from "./components/ui";
import { Home } from "./routes/Home";
import { EvidenceLayout } from "./routes/evidence/EvidenceLayout";

// Each page loads on demand, so the charting library is only fetched by pages that draw charts.
function page(load: () => Promise<Record<string, unknown>>, name: string) {
  const C = lazy(() => load().then((m) => ({ default: m[name] as ComponentType })));
  return <Suspense fallback={<Loading />}><C /></Suspense>;
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/field", element: page(() => import("./routes/Field"), "Field") },
      { path: "/risks", element: page(() => import("./routes/Risks"), "Risks") },
      { path: "/options", element: page(() => import("./routes/Options"), "Options") },
      { path: "/next", element: page(() => import("./routes/NextSteps"), "NextSteps") },
      {
        path: "/evidence", element: <EvidenceLayout />,
        children: [
          { index: true, element: page(() => import("./routes/evidence/ModelEvidence"), "ModelEvidence") },
          { path: "failures", element: page(() => import("./routes/evidence/Failures"), "Failures") },
          { path: "data", element: page(() => import("./routes/evidence/DataMethods"), "DataMethods") },
        ],
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
