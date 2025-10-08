import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App.tsx"
import "./index.css"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import Dashboard from "./pages/Dashboard.tsx"
import JobsListPage from "./pages/JobListPage.tsx"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
          <Route path="/" element={<App />}>
            <Route index element={<Dashboard />}/>
            <Route path="jobs" element={<JobsListPage />}/>
          </Route>
      </Routes>
    </BrowserRouter>  
  </React.StrictMode>,
)