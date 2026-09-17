import { BrowserRouter, Routes, Route } from "react-router";

import Login from "./pages/Login";
import Scan from "./pages/Scan";
import Review from "./pages/Review";
import ParentToday from "./pages/ParentToday";
import Dashboard from "./pages/Dashboard";
import VisitCard from "./pages/VisitCard";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />
        <Route path="/scan" element={<Scan />} />
        <Route path="/review" element={<Review />} />
        <Route path="/today" element={<ParentToday />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/visit-card" element={<VisitCard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;