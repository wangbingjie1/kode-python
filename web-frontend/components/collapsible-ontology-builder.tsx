"use client"

import { useState, useEffect } from "react"
import { ChevronRight, ChevronDown, Search, Code, PlayCircle, FileText, CheckCircle, Copy } from 'lucide-react'

interface BuildStep {
  id: string
  name: string
  icon: React.ComponentType<{ className?: string }>
  content: string
  status: 'pending' | 'active' | 'completed' | 'collapsed'
}

export function CollapsibleOntologyBuilder({ onComplete }: { onComplete?: () => void }) {
  const [steps, setSteps] = useState<BuildStep[]>([
    {
      id: 'analyze',
      name: 'Analyze',
      icon: Search,
      status: 'pending',
      content: `The manual.md file provides crucial context for understanding the payment processing data we'll be analyzing. Key observations:

1. Content Structure:
   • The document is a comprehensive guide covering payment processing optimization
   • Contains 338 lines of structured content with clear sections
   • Includes definitions of key terms and business rules

2. Key Topics Covered:
   • Merchant account types and categorization
   • Fee structures and calculation methodologies
   • Fraud prevention and reduction strategies
   • Reporting and data usage guidelines

3. Business Rules Indicated:
   • The mention of "Understanding Payment Processing Fees" suggests the fees.json file will be critical
   • References to "Merchant Category Code" aligns with merchant_category_codes.csv
   • "Authorization Characteristics Indicator" likely relates to payment attributes

4. Next Steps:
   • The manual establishes the business context we need to interpret the data files
   • We should now examine the supporting data files to understand how these business rules manifest in practice`
    },
    {
      id: 'code',
      name: 'Code',
      icon: Code,
      status: 'pending',
      content: `import pandas as pd
import json
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal

# Initialize ontology graph
g = Graph()
EX = Namespace("http://example.org/payment-ontology#")

# Define main classes
classes = [
    (EX.Payment, "Payment transaction entity"),
    (EX.Merchant, "Merchant or business entity"),
    (EX.Customer, "Customer entity"),
    (EX.Fee, "Fee structure"),
    (EX.Category, "Merchant category")
]

for cls, description in classes:
    g.add((cls, RDF.type, OWL.Class))
    g.add((cls, RDFS.comment, Literal(description)))

# Define object properties
g.add((EX.hasMerchant, RDF.type, OWL.ObjectProperty))
g.add((EX.hasCustomer, RDF.type, OWL.ObjectProperty))
g.add((EX.hasFee, RDF.type, OWL.ObjectProperty))
g.add((EX.hasCategory, RDF.type, OWL.ObjectProperty))

# Define data properties
g.add((EX.amount, RDF.type, OWL.DatatypeProperty))
g.add((EX.timestamp, RDF.type, OWL.DatatypeProperty))
g.add((EX.status, RDF.type, OWL.DatatypeProperty))

print(f"Ontology schema created with {len(g)} triples")`
    },
    {
      id: 'execute',
      name: 'Execute',
      icon: PlayCircle,
      status: 'pending',
      content: `[Executing ontology construction code...]

✓ Loaded payment data: 12,500 records
✓ Loaded merchant categories: 42 categories
✓ Loaded fee structures: 18 fee types
✓ Created entity relationships
✓ Built knowledge graph structure

Ontology Statistics:
- Total triples: 67,842
- Classes: 5
- Object properties: 12
- Data properties: 23
- Individuals: 12,500

Execution completed in 1.8 seconds`
    },
    {
      id: 'file',
      name: 'File',
      icon: FileText,
      status: 'pending',
      content: `• payment_ontology.owl (245 KB)
  Complete OWL ontology file in RDF/XML format

• payment_ontology.ttl (198 KB)
  Turtle format for better readability

• ontology_stats.json (12 KB)
  Statistical summary of the ontology structure

All files saved to: /data/ontology/`
    },
    {
      id: 'activate',
      name: 'Activate',
      icon: CheckCircle,
      status: 'pending',
      content: `Ontology activation sequence:

✓ Loading ontology into graph database
✓ Creating SPARQL endpoint
✓ Indexing entity relationships
✓ Enabling semantic query support
✓ Activating knowledge graph API

Ontology is now active and ready for queries!
Endpoint: http://localhost:7200/repositories/payments

Sample SPARQL query:
SELECT ?payment ?amount WHERE {
  ?payment rdf:type ex:Payment .
  ?payment ex:amount ?amount .
  FILTER (?amount > 1000)
}

Knowledge graph successfully deployed!`
    }
  ])

  const [currentStepIndex, setCurrentStepIndex] = useState(0)

  useEffect(() => {
    // Start the first step automatically
    const timer = setTimeout(() => {
      processStep(0)
    }, 500)

    return () => clearTimeout(timer)
  }, [])

  const processStep = (stepIndex: number) => {
    if (stepIndex >= steps.length) {
      // All steps completed
      if (onComplete) {
        setTimeout(() => {
          onComplete()
        }, 1000)
      }
      return
    }

    // Mark step as active
    setSteps(prev => {
      const newSteps = [...prev]
      newSteps[stepIndex].status = 'active'
      return newSteps
    })

    // Wait for step duration (1.6 seconds per step = 8 seconds total for 5 steps)
    setTimeout(() => {
      // Mark step as completed and collapsed
      setSteps(prev => {
        const newSteps = [...prev]
        newSteps[stepIndex].status = 'collapsed'
        return newSteps
      })

      // Process next step
      setTimeout(() => {
        processStep(stepIndex + 1)
      }, 100)
    }, 1600)
  }

  const toggleStep = (stepId: string) => {
    setSteps(prev => prev.map(step => {
      if (step.id === stepId && step.status === 'collapsed') {
        return { ...step, status: 'completed' }
      }
      if (step.id === stepId && step.status === 'completed') {
        return { ...step, status: 'collapsed' }
      }
      return step
    }))
  }

  const copyContent = (content: string) => {
    navigator.clipboard.writeText(content)
  }

  return (
    <div className="space-y-2">
      {steps.map((step) => {
        const Icon = step.icon
        const isExpanded = step.status === 'active' || step.status === 'completed'
        const isActive = step.status === 'active'
        const isCompleted = step.status === 'collapsed'

        return (
          <div 
            key={step.id}
            className={`border border-slate-200 rounded-lg overflow-hidden transition-all ${
              isActive ? 'shadow-md' : ''
            }`}
          >
            {/* Step Header */}
            <div 
              className={`flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50 ${
                isActive ? 'bg-blue-50' : 'bg-white'
              }`}
              onClick={() => toggleStep(step.id)}
            >
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-slate-600" />
              ) : (
                <ChevronRight className="w-4 h-4 text-slate-600" />
              )}
              
              <Icon className={`w-5 h-5 ${
                isCompleted ? 'text-[#10B981]' : isActive ? 'text-[#5A95A8]' : 'text-slate-400'
              }`} />
              
              <span className={`font-medium text-sm ${
                isCompleted ? 'text-slate-600' : 'text-[#2D3748]'
              }`}>
                {step.name}
              </span>

              {isCompleted && (
                <CheckCircle className="w-4 h-4 text-[#10B981] ml-auto" />
              )}

              {isExpanded && (
                <div className="ml-auto flex gap-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      copyContent(step.content)
                    }}
                    className="p-1.5 hover:bg-white rounded transition-colors"
                  >
                    <Copy className="w-4 h-4 text-slate-500" />
                  </button>
                </div>
              )}
            </div>

            {/* Step Content */}
            {isExpanded && (
              <div className="px-4 py-4 bg-slate-50 border-t border-slate-200">
                <pre className="text-xs text-slate-700 whitespace-pre-wrap font-sans leading-relaxed">
                  {step.content}
                </pre>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
