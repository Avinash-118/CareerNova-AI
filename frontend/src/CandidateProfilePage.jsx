
import React, { useEffect, useState } from "react";

const API_URL = "http://127.0.0.1:8000";

const emptyProfile = {
  profile_id: "local-candidate",
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  location: "",
  linkedin_url: "",
  github_url: "",
  portfolio_url: "",
  education: "",
  university: "",
  degree: "",
  experience_years: "",
  skills: "",
  work_authorization: "",
  sponsorship_required: "",
};

const sections = [
  {
    title: "Personal Information",
    description: "Information commonly required on job applications.",
    fields: [
      { name: "first_name", label: "First Name", required: true },
      { name: "last_name", label: "Last Name", required: true },
      { name: "email", label: "Email Address", type: "email", required: true },
      { name: "phone", label: "Phone Number", type: "tel" },
      { name: "location", label: "Current Location", placeholder: "City, State" },
    ],
  },
  {
    title: "Education & Experience",
    description: "Your academic and professional background.",
    fields: [
      { name: "university", label: "University / College" },
      { name: "degree", label: "Degree" },
      { name: "education", label: "Education Details", multiline: true },
      { name: "experience_years", label: "Years of Experience" },
      {
        name: "skills",
        label: "Technical & Professional Skills",
        multiline: true,
        placeholder: "Python, SQL, React, Machine Learning...",
      },
    ],
  },
  {
    title: "Professional Links",
    description: "Links recruiters may request.",
    fields: [
      { name: "linkedin_url", label: "LinkedIn URL", type: "url" },
      { name: "github_url", label: "GitHub URL", type: "url" },
      { name: "portfolio_url", label: "Portfolio URL", type: "url" },
    ],
  },
  {
    title: "Work Eligibility",
    description: "Provide accurate answers for future applications.",
    fields: [
      {
        name: "work_authorization",
        label: "Work Authorization Status",
        options: [
          "Authorized to work",
          "Student work authorization",
          "Not currently authorized",
          "Prefer not to say",
        ],
      },
      {
        name: "sponsorship_required",
        label: "Will you require employer sponsorship?",
        options: ["Yes", "No", "Unsure"],
      },
    ],
  },
];

export default function CandidateProfilePage() {
  const [profile, setProfile] = useState(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadProfile() {
      try {
        const response = await fetch(
          `${API_URL}/api/profile/local-candidate`
        );

        if (response.status === 404) {
          return;
        }

        if (!response.ok) {
          throw new Error("Could not load your profile.");
        }

        const data = await response.json();

        if (active) {
          setProfile({ ...emptyProfile, ...data });
        }
      } catch (err) {
        if (active) {
          setError(err.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadProfile();

    return () => {
      active = false;
    };
  }, []);

  function updateField(event) {
    const { name, value } = event.target;

    setProfile((previous) => ({
      ...previous,
      [name]: value,
    }));

    setMessage("");
    setError("");
  }

  async function saveProfile(event) {
    event.preventDefault();

    setSaving(true);
    setMessage("");
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/profile/save`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(profile),
      });

      if (!response.ok) {
        const details = await response.json().catch(() => null);

        const validationMessage = Array.isArray(details?.detail)
          ? details.detail.map((item) => item.msg).join(", ")
          : details?.detail;

        throw new Error(validationMessage || "Unable to save profile.");
      }

      setMessage("Your candidate profile was saved successfully!");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const inputStyle = {
    width: "100%",
    padding: "12px 14px",
    borderRadius: 10,
    border: "1px solid #475569",
    background: "#0f172a",
    color: "#f8fafc",
    fontSize: 14,
    boxSizing: "border-box",
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#020617",
        color: "#f8fafc",
        padding: "40px 20px",
      }}
    >
      <div style={{ maxWidth: 920, margin: "0 auto" }}>
        <div style={{ marginBottom: 30 }}>
          <p style={{ color: "#38bdf8", fontWeight: 600 }}>
            CareerNova AI
          </p>

          <h1 style={{ fontSize: 32, marginBottom: 10 }}>
            My Candidate Profile
          </h1>

          <p style={{ color: "#94a3b8", lineHeight: 1.6 }}>
            Save your information once. CareerNova AI can use this
            profile to help fill job applications in a future step.
          </p>
        </div>

        {loading ? (
          <p>Loading your profile...</p>
        ) : (
          <form onSubmit={saveProfile}>
            {sections.map((section) => (
              <section
                key={section.title}
                style={{
                  background: "#111827",
                  border: "1px solid #334155",
                  borderRadius: 16,
                  padding: 24,
                  marginBottom: 22,
                }}
              >
                <h2 style={{ fontSize: 21, marginBottom: 6 }}>
                  {section.title}
                </h2>

                <p
                  style={{
                    color: "#94a3b8",
                    fontSize: 14,
                    marginBottom: 24,
                  }}
                >
                  {section.description}
                </p>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fit, minmax(250px, 1fr))",
                    gap: 20,
                  }}
                >
                  {section.fields.map((field) => (
                    <div key={field.name}>
                      <label
                        htmlFor={field.name}
                        style={{
                          display: "block",
                          marginBottom: 8,
                          fontWeight: 500,
                          fontSize: 14,
                        }}
                      >
                        {field.label}
                        {field.required ? " *" : ""}
                      </label>

                      {field.multiline ? (
                        <textarea
                          id={field.name}
                          name={field.name}
                          value={profile[field.name] || ""}
                          onChange={updateField}
                          placeholder={field.placeholder || ""}
                          rows={4}
                          style={{
                            ...inputStyle,
                            resize: "vertical",
                          }}
                        />
                      ) : field.options ? (
                        <select
                          id={field.name}
                          name={field.name}
                          value={profile[field.name] || ""}
                          onChange={updateField}
                          style={inputStyle}
                        >
                          <option value="">Select an option</option>

                          {field.options.map((option) => (
                            <option key={option} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          id={field.name}
                          name={field.name}
                          type={field.type || "text"}
                          required={Boolean(field.required)}
                          value={profile[field.name] || ""}
                          onChange={updateField}
                          placeholder={field.placeholder || ""}
                          style={inputStyle}
                        />
                      )}
                    </div>
                  ))}
                </div>
              </section>
            ))}

            {message && (
              <p
                role="status"
                style={{ color: "#4ade80", marginBottom: 16 }}
              >
                {message}
              </p>
            )}

            {error && (
              <p
                role="alert"
                style={{ color: "#f87171", marginBottom: 16 }}
              >
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={saving}
              style={{
                background: "#2563eb",
                color: "white",
                border: "none",
                borderRadius: 10,
                padding: "14px 30px",
                fontSize: 16,
                fontWeight: 600,
                cursor: saving ? "wait" : "pointer",
                opacity: saving ? 0.7 : 1,
              }}
            >
              {saving ? "Saving..." : "Save Candidate Profile"}
            </button>

            <p
              style={{
                marginTop: 16,
                fontSize: 12,
                color: "#94a3b8",
              }}
            >
              Local development only. This profile API does not yet
              have user authentication. Do not deploy it publicly
              or store sensitive information until security is added.
            </p>
          </form>
        )}
      </div>
    </main>
  );
}
