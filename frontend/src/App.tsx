import { NavLink, Outlet } from "react-router-dom"

export default function App() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      {/* Nav bar */}
      <nav className="bg-white w-full top-0 sticky z-50 rounded px-4 py-2 mb-4 flex gap-4 shadow-md">
        <div className="w-full px-6 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Left: App Name */}
            <h1 className="text-2xl font-bold text-gray-800">Job Applications</h1>

            {/* Right: Navigation links */}
            <div className="flex space-x-6">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `text-gray-700 hover:text-blue-600 font-medium ${
                    isActive ? "text-blue-600 border-b-2 border-blue-600" : ""
                  }`
                }
              >
                Dashboard
              </NavLink>
              <NavLink
                to="/jobs"
                className={({ isActive }) =>
                  `text-gray-700 hover:text-blue-600 font-medium ${
                    isActive ? "text-blue-600 border-b-2 border-blue-600" : ""
                  }`
                }
              >
                Jobs
              </NavLink>
            </div>
          </div>
        </div>
      </nav>

      <Outlet/>
    </div>
  )
}

