import { render, screen } from "@testing-library/react";
import DashboardMetrics from "../src/components/DashboardMetrics";

test("renders all dashboard metric cards with their counts", () => {
    render(
        <DashboardMetrics
            total={10}
            applied={4}
            interviewing={2}
            offers={1}
            rejected={3}
        />
    );

    expect(screen.getByLabelText(/dashboard metrics/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/stats card for total jobs/i)).toHaveTextContent("10");
    expect(screen.getByLabelText(/stats card for applied/i)).toHaveTextContent("4");
    expect(screen.getByLabelText(/stats card for interviewing/i)).toHaveTextContent("2");
    expect(screen.getByLabelText(/stats card for offers/i)).toHaveTextContent("1");
    expect(screen.getByLabelText(/stats card for rejected/i)).toHaveTextContent("3");
});
