import React from "react"
import StatsCard from "./StatsCard"

interface DashboardMetricsProps {
    total: number;
    applied: number;
    interviewing: number;
    offers: number;
    rejected: number;
}

const DashboardMetrics: React.FC<DashboardMetricsProps> = ({
    total,
    applied,
    interviewing,
    offers,
    rejected,
}) => {
    return(
        <div
            className="grid grid-cols2 sm:grid-cols-5 gap-4 mb-6"
            aria-label="dashboard metrics"
        >
            <StatsCard title="Total Jobs" value={total} color="bg-gray-100"/>
            <StatsCard title="Applied" value={applied} color="bg-blue-100"/>
            <StatsCard title="Interviewing" value={interviewing} color="bg-yellow-100"/>
            <StatsCard title="Offers" value={offers} color="bg-green-100"/>
            <StatsCard title="Rejected" value={rejected} color="bg-red-100"/>
        </div>
    );
};

export default DashboardMetrics;