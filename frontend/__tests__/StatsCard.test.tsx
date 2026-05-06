import { render, screen } from "@testing-library/react";
import StatsCard from "../src/components/StatsCard";

test("renders title and value with default background styling", () => {
    render(<StatsCard title="Applied" value={12} />);

    const card = screen.getByLabelText(/stats card for applied/i);
    expect(card).toBeInTheDocument();
    expect(card).toHaveClass("bg-white");
    expect(screen.getByText("Applied")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
});

test("applies a custom background color class when provided", () => {
    render(<StatsCard title="Offers" value="3" color="bg-green-100" />);

    expect(screen.getByLabelText(/stats card for offers/i)).toHaveClass("bg-green-100");
});
