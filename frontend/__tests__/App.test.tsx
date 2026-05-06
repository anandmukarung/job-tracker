import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import App from "../src/App";

function renderApp(initialPath = "/") {
    return render(
        <MemoryRouter initialEntries={[initialPath]}>
            <Routes>
                <Route path="/" element={<App />}>
                    <Route index element={<div>Dashboard Page</div>} />
                    <Route path="jobs" element={<div>Jobs Page</div>} />
                </Route>
            </Routes>
        </MemoryRouter>
    );
}

test("renders navigation and outlet content for the dashboard route", () => {
    renderApp("/");

    expect(screen.getByText("Job Applications")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /dashboard/i })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Dashboard Page")).toBeInTheDocument();
});

test("marks the jobs link active on the jobs route", () => {
    renderApp("/jobs");

    expect(screen.getByRole("link", { name: /jobs/i })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Jobs Page")).toBeInTheDocument();
});
