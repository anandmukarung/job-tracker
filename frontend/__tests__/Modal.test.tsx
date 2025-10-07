import { render, screen, fireEvent } from "@testing-library/react";
import Modal from "../src/components/Modal";
import { vi } from "vitest";

describe("Modal Component", () => {
    test("renders children properly", () => {
        const mockClose = vi.fn();

        render(
            <Modal onClose={mockClose}>
                <p>Modal Content Here</p>
            </Modal>
        );

        expect(screen.getByText(/modal content here/i)).toBeInTheDocument();
    });

    test("calls onClose when clicking the close button", () => {
        const mockClose = vi.fn();
        render(
        <Modal onClose={mockClose}>
            <p>Test Modal</p>
        </Modal>
        );

        const closeButton = screen.getByLabelText(/close-modal/i);
        fireEvent.click(closeButton);
        expect(mockClose).toHaveBeenCalledTimes(1);
    });

    test("does NOT close when clicking background", () => {
    const mockClose = vi.fn();
    render(
        <Modal onClose={mockClose}>
        <p>Form Content</p>
        </Modal>
    );

    const overlay = screen.getByLabelText(/modal-overlay/i);
    fireEvent.click(overlay);
    expect(mockClose).not.toHaveBeenCalled();
    });
});