import { mockJobs } from "./MockJobs";
import { vi } from "vitest"

// mock the whole jobs API module
vi.mock("../../api/jobs", () => ({
  createJob: vi.fn().mockResolvedValue({... mockJobs[0]}),
  updateJob: vi.fn().mockResolvedValue({... mockJobs[1]}),
}));

import { act, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import JobForm from "../JobForm";
import { createJob, updateJob } from "../../api/jobs";

test("all input fields are being rendered with proper initial values", async() => {
    render(<JobForm/>);

    // Check all inputs by label
    expect(screen.getByLabelText(/job title/i)).toHaveValue("");
    expect(screen.getByLabelText(/company name/i)).toHaveValue("");
    expect(screen.getByLabelText(/job location/i)).toHaveValue("");
    expect(screen.getByLabelText(/job status/i)).toHaveDisplayValue("Saved");
    expect(screen.getByLabelText(/application date/i)).toHaveValue("");
    expect(screen.getByLabelText(/follow-up date/i)).toHaveValue("");
    expect(screen.getByLabelText(/job link/i)).toHaveValue("");
    expect(screen.getByLabelText(/job description/i)).toHaveValue("");
    expect(screen.getByLabelText(/job board id/i)).toHaveValue("");
    expect(screen.getByLabelText(/job source/i)).toHaveValue("");
    expect(screen.getByLabelText(/job notes/i)).toHaveValue("");
    expect(screen.getByLabelText(/submit/i)).toHaveTextContent("Add Job");
});

test("edit mode renders pre-filled data for job", async() => {
    // initial data means it should go into edit mode
    render(<JobForm initialData={mockJobs[0]} onSubmitted={vi.fn()}/>)

    // Expect the initial saved state of job to be displayed
    expect(screen.getByLabelText(/job title/i)).toHaveValue(mockJobs[0].title);
    expect(screen.getByLabelText(/company name/i)).toHaveValue(mockJobs[0].company);
    expect(screen.getByLabelText(/job location/i)).toHaveValue(mockJobs[0].location);
    expect(screen.getByLabelText(/job status/i)).toHaveDisplayValue(mockJobs[0].status);
    expect(screen.getByLabelText(/application date/i)).toHaveValue(mockJobs[0].applied_date);
    expect(screen.getByLabelText(/follow-up date/i)).toHaveValue("");
    expect(screen.getByLabelText(/job link/i)).toHaveValue(mockJobs[0].job_link);
    expect(screen.getByLabelText(/job description/i)).toHaveValue(mockJobs[0].job_description);
    expect(screen.getByLabelText(/job board id/i)).toHaveValue(mockJobs[0].job_board_id);
    expect(screen.getByLabelText(/job source/i)).toHaveValue(mockJobs[0].source);
    expect(screen.getByLabelText(/job notes/i)).toHaveValue(mockJobs[0].notes);
    expect(screen.getByLabelText(/submit/i)).toHaveTextContent("Update Job");

});

test("shows error when required fields are empty", async () => {
    const mockOnSubmitted = vi.fn()
    render(<JobForm onSubmitted={vi.fn()} />);

    // click submit without filling any inputs
    await userEvent.click(screen.getByLabelText('submit'));

    // check that error message is displayed
    expect(
        await screen.findByText(/must specify title, company and location/i)
    ).toBeInTheDocument();

    // onSubmitted should NOT have been called
    expect(mockOnSubmitted).not.toHaveBeenCalled();
})


test("successful job addition when required fields are met", async () => {
    const mockOnSubmitted = vi.fn()
    render(<JobForm onSubmitted={mockOnSubmitted} />);

    // fill inputs
    await userEvent.type(screen.getByLabelText(/title/i), mockJobs[0].title);
    await userEvent.type(screen.getByLabelText(/company/i), mockJobs[0].company);
    await userEvent.type(screen.getByLabelText(/location/i), mockJobs[0].location);

    // click submit
    const submitButton = screen.getByLabelText('submit');
    await act (async () => {
        await userEvent.click(submitButton);
    });
        
    // check createJob() is being called with correct payload
    await vi.waitFor(() => {
        expect(createJob).toHaveBeenCalledWith(
            expect.objectContaining({
                title: mockJobs[0].title,
                company: mockJobs[0].company,
                location: mockJobs[0].location,
            })
        );
    });
    // onSubmitted SHOULD have been called 
    expect(mockOnSubmitted).toHaveBeenCalled()

    // Check all inputs have been reset
    await waitFor(() => {
        expect(screen.getByLabelText(/job title/i)).toHaveValue("");
        expect(screen.getByLabelText(/company name/i)).toHaveValue("");
        expect(screen.getByLabelText(/job location/i)).toHaveValue("");
        expect(screen.getByLabelText(/job status/i)).toHaveDisplayValue("Saved");
        expect(screen.getByLabelText(/application date/i)).toHaveValue("");
        expect(screen.getByLabelText(/follow-up date/i)).toHaveValue("");
        expect(screen.getByLabelText(/job link/i)).toHaveValue("");
        expect(screen.getByLabelText(/job description/i)).toHaveValue("");
        expect(screen.getByLabelText(/job board id/i)).toHaveValue("");
        expect(screen.getByLabelText(/job source/i)).toHaveValue("");
        expect(screen.getByLabelText(/job notes/i)).toHaveValue("");
        expect(screen.getByLabelText(/submit/i)).toHaveTextContent("Add Job");
    });
   
});

test("successful job editing ", async () => {
    const mockOnSubmitted = vi.fn();
    // render with existing data mockJobs[0]
    render(<JobForm initialData={mockJobs[0]} onSubmitted={mockOnSubmitted} />);

    // clear existing data
    await userEvent.clear(screen.getByLabelText(/title/i));
    await userEvent.clear(screen.getByLabelText(/company/i));
    await userEvent.clear(screen.getByLabelText(/location/i));
    
    // re-fill inputs
    await userEvent.type(screen.getByLabelText(/title/i), mockJobs[1].title);
    await userEvent.type(screen.getByLabelText(/company/i), mockJobs[1].company);
    await userEvent.type(screen.getByLabelText(/location/i), mockJobs[1].location);

    // click submit
    const submitButton = screen.getByLabelText('submit');
    await userEvent.click(submitButton);
    
    // check that updateJob() is being called with origial id and changed payload
    await vi.waitFor(() => {
        expect(updateJob).toHaveBeenCalledWith(mockJobs[0].id,
            expect.objectContaining({
                title: mockJobs[1].title,
                company: mockJobs[1].company,
                location: mockJobs[1].location,
            })
        );
    });
       // onSubmitted SHOULD have been called 
    expect(mockOnSubmitted).toHaveBeenCalled()
   
});


