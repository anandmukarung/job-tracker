import { render, screen, fireEvent, within} from "@testing-library/react"
import JobTable from "../JobTable"
import { vi } from "vitest"
import { mockJobs } from "./MockJobs"

test("Displays No Jobs Found if jobs list empty", () => {
    render(
        <JobTable
            jobs={[]}
            onDelete={() => {}}
            onEdit={() => {}}
        />
    )
    expect(screen.getByText(/no jobs found./i)).toBeInTheDocument();
});

test("renders job details", () => {
    render(
        <JobTable
            jobs={mockJobs}
            onDelete={() => {}}
            onEdit={() => {}}
        />
    )
    // check in document for mock job details
    const row = screen.getByTestId(`job-row-${mockJobs[0].id}`);
    expect(within(row).getByText(`${mockJobs[0].title}`)).toBeInTheDocument();
    expect(within(row).getByText(`${mockJobs[0].company}`)).toBeInTheDocument();
    expect(within(row).getByText(`${mockJobs[0].location}`)).toBeInTheDocument();
    expect(within(row).getByText(`${mockJobs[0].status}`)).toBeInTheDocument();
});  

test("shows edit and delete buttons", () => {
    render(
        <JobTable
            jobs={mockJobs}
            onDelete={() => {}}
            onEdit={() => {}}
        />
    )
    // check in document
    const deleteBtn = screen.getByTestId(`delete-${mockJobs[0].id}`);
    expect(deleteBtn).toBeInTheDocument();
    const editBtn = screen.getByTestId(`edit-${mockJobs[0].id}`);
    expect(editBtn).toBeInTheDocument();
});

test("delete button calls handler after confirm", () => {
    // mock confirm to auto-return true
    vi.spyOn(window, "confirm").mockReturnValueOnce(true);
    // mock delete function
    const handleDelete = vi.fn()
  
    render(
        <JobTable
            jobs={mockJobs}
            onDelete={handleDelete}
            onEdit={() => {}}
        />
    )
    const deleteBtn = screen.getByTestId(`delete-${mockJobs[0].id}`);
    fireEvent.click(deleteBtn);
    //confirm delete handler called with job id
    expect(handleDelete).toHaveBeenCalledWith(1); 
});

test("delete button does not call handler if not confirmed", () => {
    // mock confirm to auto-return false
     vi.spyOn(window, "confirm").mockReturnValueOnce(false);
    // mock delete function
    const handleDelete = vi.fn()
    
    render(
        <JobTable
            jobs={mockJobs}
            onDelete={handleDelete}
            onEdit={() => {}}
        />
    )
    const deleteBtn = screen.getByTestId(`delete-${mockJobs[0].id}`);
    fireEvent.click(deleteBtn);
    //confirm delete handler not called
    expect(handleDelete).not.toHaveBeenCalled();
});

test("edit button calls handler with job", () => {
    // mock delete function
    const handleEdit = vi.fn()
  
    render(
        <JobTable
            jobs={mockJobs}
            onDelete={() => {}}
            onEdit={handleEdit}
        />
    )
    const eidtButton = screen.getByTestId(`edit-${mockJobs[0].id}`);
    fireEvent.click(eidtButton);
    //confirm edit handler called with job object
    expect(handleEdit).toHaveBeenCalledWith(mockJobs[0]); 
});

test("renders a hyperlink with source when job_link exists", () => {
    render(<JobTable jobs={mockJobs} onDelete={() => {}} onEdit={() => {}} />);
    // get row of job with link
    const row = screen.getByTestId(`job-row-${mockJobs[0].id}`);
    const link = within(row).getByRole("link", {name: new RegExp(`${mockJobs[0].source}`)});
    // check href,target & rel
    expect(link).toHaveAttribute(
        "href",
        `${mockJobs[0].job_link}`
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");

});

test("displays N/A when no job link and no source ", () => {
    render(<JobTable jobs={mockJobs} onDelete={() => {}} onEdit={() => {}} />);
    // find the cell
    const row = screen.getByTestId(`job-row-${mockJobs[3].id}`);
    expect(within(row).getByText("N\/A")).toBeInTheDocument();
});

test("displays only source when no link for job", () => {
    render(<JobTable jobs={mockJobs} onDelete={() => {}} onEdit={() => {}} />);
    // find the cell
    const row = screen.getByTestId(`job-row-${mockJobs[4].id}`);
    expect(within(row).getByText(`${mockJobs[4].source}`)).toBeInTheDocument();
    expect(within(row).queryByRole("link")).not.toBeInTheDocument();
});