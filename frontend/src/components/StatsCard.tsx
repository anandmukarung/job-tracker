import React from "react"

interface StatsCardProps {
    title: string;
    value: number | string;
    color?: string;
}

const StatsCard: React.FC<StatsCardProps> = ({ title, value, color }) => {
    return (
        <div
            className={`rounded-2x1 shadow-md p-4 flex flex-col justify-center items-center transition-transform transfrom hover:scale-105 duration-200 ${color || "bg-white"}`}
            aria-label={`stats card for ${title}`}
        >
            <h3 className="text-gray-500 text-sm font-semibold">{title}</h3>
            <p className="text-2x1 font-bold text-gray-800">{value}</p>
        </div>
    );
};

export default StatsCard;