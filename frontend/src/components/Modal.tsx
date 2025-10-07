import React from "react";

type ModalProps = {
    children: React.ReactNode;
    onClose: () => void;
}

export default function Modal({children, onClose}: ModalProps){
    return (
        <div aria-label= "modal-overlay"  className="items-start items-start overflow-y-auto fixed inset-0 flex justify-center bg-black bg-opacity-50 z-50">
            {/*Inner Div = Modal Content Box */}
            <div aria-label="model-content" className="overflow-y-auto sm:mt-0 bg-white rounded-lg p-6 max-w-md relative shadow-lg">
                {/*Close Button*/}
                <button
                    aria-label="close-modal"
                    onClick={() => {
                        const confirmCancel = window.confirm("Are you sure you want to exit? Unsaved changes will be lost.");
                        if (confirmCancel) {
                            onClose();
                        }
                    }}
                    className="absolute text-lg top-2 right-2 text-gray-500 hover:text-black"
                >
                    X
                </button>
                {children}
            </div>
        </div>
    );
}