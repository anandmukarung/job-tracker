import React from "react";

type ModalProps = {
    children: React.ReactNode;
    onClose: () => void;
}

export default function Modal({children, onClose}: ModalProps){
    return (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50">
            {/*Inner Div = Modal Content Box */}
            <div className="bg-white rounded-lg p-6 w-full max-w-md relative shadow-lg">
                {/*Close Button*/}
                <button 
                    onClick={onClose}
                    className="absolute top-2 right-2 text-gray-500 hover:text-black"
                >
                    x
                </button>
                {children}
            </div>
        </div>
    );
}