"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { Check, Loader2, FileText, Database, Shield, Droplets, Shuffle, Zap, Upload, Network } from 'lucide-react'

type StepStatus = "pending" | "processing" | "completed" | "current"

interface ETLStep {
  id: number
  name: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  status: StepStatus
}

export function SimplifiedETLView({ 
  onComplete, 
  buildOntology = false,
  buildingStage,
}: { 
  onComplete?: () => void
  buildOntology?: boolean
  buildingStage?: string
}) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [agentLogs, setAgentLogs] = useState<string[]>([])
  const [generatedCode, setGeneratedCode] = useState("")

  const [steps, setSteps] = useState<ETLStep[]>([
    { id: 1, name: "Extraction", label: "Extract", icon: Database, status: "current" },
    { id: 2, name: "Profiling", label: "Profile", icon: FileText, status: "pending" },
    { id: 3, name: "Validation", label: "Validate", icon: Shield, status: "pending" },
    { id: 4, name: "Cleaning", label: "Clean", icon: Droplets, status: "pending" },
    { id: 5, name: "Normalization", label: "Normalize", icon: Shuffle, status: "pending" },
    { id: 6, name: "Transformation", label: "Transform", icon: Zap, status: "pending" },
    { id: 7, name: "Load", label: "Load", icon: Upload, status: "pending" },
    { id: 8, name: "Ontology", label: "Ontology", icon: Network, status: "pending" },
  ])

  useEffect(() => {
    // Only auto-start if not in questions stage (in questions stage, keep showing last ETL step)
    if (buildingStage !== 'questions') {
      console.log("[v0] ETL View mounted, starting auto-processing")
      const timer = setTimeout(() => {
        processStep(0)
      }, 500)

      return () => clearTimeout(timer)
    } else {
      console.log("[v0] In questions stage, keeping ETL at last step")
    }
  }, [buildingStage])

  useEffect(() => {
    if (buildOntology && steps[currentStepIndex].name !== "Ontology") {
      console.log("[v0] Starting ontology building")
      processOntologyStep()
    }
  }, [buildOntology])

  const processStep = (stepIndex: number) => {
    // Stop at step 7 (Load), don't process Ontology automatically
    if (stepIndex >= 7) {
      console.log("[v0] Data governance steps completed, waiting for user confirmation")
      if (onComplete) {
        setTimeout(() => {
          onComplete()
        }, 500)
      }
      return
    }

    console.log(`[v0] Processing step ${stepIndex + 1}: ${steps[stepIndex].name}`)

    setAgentLogs([])
    setGeneratedCode("")

    const stepName = steps[stepIndex].name

    setSteps((prevSteps) => {
      const newSteps = [...prevSteps]
      newSteps[stepIndex].status = "processing"
      return newSteps
    })

    const logs = [
      `[Agent] Starting ${stepName} process...`,
      `[Agent] Analyzing and generating ${stepName.toLowerCase()} code...`,
      `[Agent] ${stepName} complete ✓`,
    ]

    const codeTemplates: Record<string, string> = {
      Extraction: `import pandas as pd
import matplotlib.pyplot as plt

# Load a sample of the payments data (first 100,000 rows for initial exploration)
payments_sample = pd.read_csv('payments.csv', nrows=100000)

# Display basic information about the dataset
print('Payments Data Sample Information:')
print(f"Number of rows: {len(payments_sample)}")
print(f"Number of columns: {len(payments_sample.columns)}")
print('\\nColumn Data Types:')
print(payments_sample.dtypes)`,
      Profiling: `# Check for missing values
print('\\nMissing Values per Column:')
print(payments_sample.isnull().sum())

# Analyze data distributions
print('\\nData Distribution Analysis:')
print(payments_sample.describe(include='all'))

# Check for duplicates
duplicates = payments_sample.duplicated().sum()
print(f'\\nDuplicate rows: {duplicates}')`,
      Validation: `# Validate data types
print('\\nData Type Validation:')
for col in payments_sample.columns:
    print(f"{col}: {payments_sample[col].dtype}")

# Check for data integrity
print('\\nData Integrity Checks:')
print(f"Null values: {payments_sample.isnull().sum().sum()}")`,
      Cleaning: `# Remove duplicates
payments_clean = payments_sample.drop_duplicates()
print(f'Removed {len(payments_sample) - len(payments_clean)} duplicate rows')

# Handle missing values
payments_clean = payments_clean.fillna(method='ffill')
print('Missing values handled')`,
      Normalization: `# Normalize numeric columns
from sklearn.preprocessing import StandardScaler

scaler = StandardScaler()
numeric_cols = payments_clean.select_dtypes(include=['float64', 'int64']).columns
payments_clean[numeric_cols] = scaler.fit_transform(payments_clean[numeric_cols])

print('Numeric columns normalized')`,
      Transformation: `# Apply transformations
payments_transformed = payments_clean.copy()

# Add derived columns
payments_transformed['transaction_year'] = pd.to_datetime(payments_transformed['date']).dt.year
payments_transformed['transaction_month'] = pd.to_datetime(payments_transformed['date']).dt.month

print('Transformations applied successfully')`,
      Load: `# Load data into target system
from sqlalchemy import create_engine

engine = create_engine('postgresql://localhost/datawarehouse')
payments_transformed.to_sql('payments', engine, if_exists='replace', index=False)

print(f'Successfully loaded {len(payments_transformed)} records into database')
print('Data governance process complete!')`,
    }

    let logIndex = 0
    const logInterval = setInterval(() => {
      if (logIndex < logs.length) {
        setAgentLogs((prev) => [...prev, logs[logIndex]])

        if (logIndex === 1) {
          setGeneratedCode(codeTemplates[stepName] || "# Code generated successfully")
        }

        logIndex++
      } else {
        clearInterval(logInterval)

        setTimeout(() => {
          setSteps((prevSteps) => {
            const newSteps = [...prevSteps]
            newSteps[stepIndex].status = "completed"
            if (stepIndex < 6) {  
              newSteps[stepIndex + 1].status = "current"
            }
            return newSteps
          })

          setTimeout(() => {
            processStep(stepIndex + 1)
          }, 200)
        }, 400)
      }
    }, 400)
  }

  const processOntologyStep = () => {
    const ontologyStepIndex = 7
    
    setSteps((prevSteps) => {
      const newSteps = [...prevSteps]
      newSteps[ontologyStepIndex].status = "processing"
      return newSteps
    })

    const logs = [
      "[Agent] Starting Ontology construction...",
      "[Agent] Analyzing data relationships and semantics...",
      "[Agent] Building knowledge graph structure...",
      "[Agent] Generating entity relationships...",
      "[Agent] Ontology construction complete ✓",
    ]

    const ontologyCode = `# Ontology Construction
from rdflib import Graph, Namespace, RDF, RDFS, OWL
import json

# Initialize knowledge graph
g = Graph()
EX = Namespace("http://example.org/ontology#")

# Define classes
g.add((EX.Payment, RDF.type, OWL.Class))
g.add((EX.Merchant, RDF.type, OWL.Class))
g.add((EX.Customer, RDF.type, OWL.Class))

# Define properties
g.add((EX.hasAmount, RDF.type, OWL.DatatypeProperty))
g.add((EX.hasMerchant, RDF.type, OWL.ObjectProperty))
g.add((EX.hasCustomer, RDF.type, OWL.ObjectProperty))

# Populate ontology with data instances
for idx, row in payments_transformed.iterrows():
    payment_uri = EX[f"Payment_{idx}"]
    g.add((payment_uri, RDF.type, EX.Payment))
    g.add((payment_uri, EX.hasAmount, row['amount']))
    
print(f'Ontology built with {len(g)} triples')
print('Knowledge graph ready for querying!')`

    setAgentLogs([])
    setGeneratedCode("")

    let logIndex = 0
    const logInterval = setInterval(() => {
      if (logIndex < logs.length) {
        setAgentLogs((prev) => [...prev, logs[logIndex]])

        if (logIndex === 2) {
          setGeneratedCode(ontologyCode)
        }

        logIndex++
      } else {
        clearInterval(logInterval)

        setTimeout(() => {
          setSteps((prevSteps) => {
            const newSteps = [...prevSteps]
            newSteps[ontologyStepIndex].status = "completed"
            return newSteps
          })

          if (onComplete) {
            setTimeout(() => {
              onComplete()
            }, 500)
          }
        }, 400)
      }
    }, 500)
  }

  const getStepStatusIcon = (step: ETLStep) => {
    const IconComponent = step.icon

    switch (step.status) {
      case "completed":
        return (
          <div className="relative">
            <div className="w-12 h-12 rounded-full bg-[#10B981] flex items-center justify-center shadow-sm">
              <Check className="w-6 h-6 text-white" strokeWidth={3} />
            </div>
            <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[#10B981] border-2 border-white flex items-center justify-center">
              <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />
            </div>
          </div>
        )
      case "processing":
        return (
          <div className="w-12 h-12 rounded-full bg-[#5A95A8] flex items-center justify-center shadow-lg animate-pulse">
            <Loader2 className="w-6 h-6 text-white animate-spin" />
          </div>
        )
      case "current":
        return (
          <div className="w-12 h-12 rounded-full bg-[#5A95A8] flex items-center justify-center shadow-md ring-4 ring-[#7AB8CC] ring-opacity-40">
            <IconComponent className="w-6 h-6 text-white" />
          </div>
        )
      default:
        return (
          <div className="w-12 h-12 rounded-full bg-white border-2 border-[#E5E7EB] flex items-center justify-center">
            <IconComponent className="w-6 h-6 text-[#6B7280]" />
          </div>
        )
    }
  }

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* Steps Progress Bar */}
      <div>
        <div className="relative">
          {/* Progress Line */}
          <div className="absolute top-6 left-6 right-6 h-0.5 bg-[#E5E7EB]">
            <div
              className="h-full bg-[#10B981] transition-all duration-500"
              style={{ width: `${(steps.filter((s) => s.status === "completed").length / (steps.length - 1)) * 100}%` }}
            />
          </div>

          {/* Steps */}
          <div className="relative flex justify-between">
            {steps.map((step) => (
              <div key={step.id} className="flex flex-col items-center" style={{ width: "12.5%" }}>
                {getStepStatusIcon(step)}
                <span
                  className={`mt-2 text-xs font-medium ${
                    step.status === "completed"
                      ? "text-[#10B981]"
                      : step.status === "current" || step.status === "processing"
                        ? "text-[#5A95A8]"
                        : "text-[#6B7280]"
                  }`}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Code Generation Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-3 h-3 rounded-full bg-[#EF4444]" />
          <div className="w-3 h-3 rounded-full bg-[#F59E0B]" />
          <div className="w-3 h-3 rounded-full bg-[#10B981]" />
          <span className="ml-2 text-sm font-medium text-[#2D3748]">Code</span>
        </div>

        <div className="flex-1 overflow-auto bg-[#1A202C] rounded-lg p-4">
          <pre className="text-sm text-[#E2E8F0] font-mono">
            <code>{generatedCode || "# Code will be generated during processing..."}</code>
          </pre>
        </div>
      </div>

      {/* Agent Work Area */}
      <div className="pt-4">
        <h4 className="text-sm font-semibold text-[#2D3748] mb-3">Agent Work Area</h4>
        <div className="space-y-2 max-h-48 overflow-auto">
          {agentLogs.length === 0 ? (
            <p className="text-sm text-[#6B7280] italic">Agent logs will appear here during processing...</p>
          ) : (
            agentLogs.map((log, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 text-sm text-[#2D3748] animate-in fade-in slide-in-from-left-2"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-[#10B981] mt-1.5 flex-shrink-0" />
                <span>{log}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
