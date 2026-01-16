"use client"

import { useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { ArrowLeft, Database, CheckCircle2, Loader2, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"
import { dataSourceApi, getErrorMessage } from "@/lib/api"

type DatabaseType = "mysql" | "postgresql" | "mongodb" | "redis"

const databases = [
  { id: "mysql" as const, label: "MySQL" },
  { id: "postgresql" as const, label: "PostgreSQL" },
  { id: "mongodb" as const, label: "MongoDB" },
  { id: "redis" as const, label: "Redis" },
]

interface TableInfo {
  name: string
  rows: number
  checked: boolean
}

export function DatabaseConnectionSection({ onBack }: { onBack: () => void }) {
  const router = useRouter()
  const params = useParams()
  const projectId = params.projectId as string

  const [selectedDb, setSelectedDb] = useState<DatabaseType>("mysql")
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [tables, setTables] = useState<TableInfo[]>([])

  // 表单数据 - 受控组件
  const [formData, setFormData] = useState({
    host: "db.myshop.com",
    port: "3306",
    database: "ecommerce_prod",
    username: "analyst_user",
    password: "password123",
  })

  const handleInputChange = (field: keyof typeof formData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [field]: e.target.value }))
    // 输入变化时重置连接状态
    if (isConnected) {
      setIsConnected(false)
      setTables([])
    }
    setError(null)
  }

  const handleDbTypeChange = (dbType: DatabaseType) => {
    setSelectedDb(dbType)
    // 切换数据库类型时重置状态
    setIsConnected(false)
    setTables([])
    setError(null)
    // 根据数据库类型设置默认端口
    const defaultPorts: Record<DatabaseType, string> = {
      mysql: "3306",
      postgresql: "5432",
      mongodb: "27017",
      redis: "6379",
    }
    setFormData(prev => ({ ...prev, port: defaultPorts[dbType] }))
  }

  const handleTestConnection = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await dataSourceApi.testConnection({
        type: selectedDb,
        host: formData.host,
        port: parseInt(formData.port, 10),
        database: formData.database,
        username: formData.username,
        password: formData.password,
      })

      if (response.success) {
        setIsConnected(true)
        // 如果后端返回了表信息，使用真实数据
        if (response.details?.tables && Array.isArray(response.details.tables)) {
          setTables(response.details.tables.map((t: unknown) => {
            if (typeof t === 'string') {
              return { name: t, rows: 0, checked: true }
            }
            const table = t as { name?: string; rows?: number }
            return {
              name: table.name || 'unknown',
              rows: table.rows || 0,
              checked: true,
            }
          }))
        }
      } else {
        setError(response.message || '连接失败')
        setIsConnected(false)
      }
    } catch (err) {
      setError(getErrorMessage(err))
      setIsConnected(false)
    } finally {
      setIsLoading(false)
    }
  }

  const handleImport = () => {
    router.push(`/projects/${projectId}/clean`)
  }

  const toggleTable = (index: number) => {
    setTables(tables.map((t, i) => (i === index ? { ...t, checked: !t.checked } : t)))
  }

  return (
    <div className="container max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight">Connect Data Source</h1>
          <p className="text-muted-foreground">Configure your database connection</p>
        </div>
      </div>

      <div className="space-y-4">
        <Label>Select Database Type</Label>
        <div className="flex gap-3">
          {databases.map((db) => (
            <Button
              key={db.id}
              variant={selectedDb === db.id ? "default" : "outline"}
              onClick={() => handleDbTypeChange(db.id)}
              className="flex-1"
              disabled={isLoading}
            >
              {db.label}
            </Button>
          ))}
        </div>
      </div>

      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-lg">
            {databases.find(db => db.id === selectedDb)?.label} Connection
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="host">Host</Label>
              <Input
                id="host"
                value={formData.host}
                onChange={handleInputChange("host")}
                className="bg-secondary border-border"
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="port">Port</Label>
              <Input
                id="port"
                value={formData.port}
                onChange={handleInputChange("port")}
                className="bg-secondary border-border"
                disabled={isLoading}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="database">Database</Label>
            <Input
              id="database"
              value={formData.database}
              onChange={handleInputChange("database")}
              className="bg-secondary border-border"
              disabled={isLoading}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={formData.username}
                onChange={handleInputChange("username")}
                className="bg-secondary border-border"
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={formData.password}
                onChange={handleInputChange("password")}
                className="bg-secondary border-border"
                disabled={isLoading}
              />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-destructive bg-destructive/10 p-3 rounded-md">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <div className="flex items-center gap-2">
            <Button
              onClick={handleTestConnection}
              variant={isConnected ? "outline" : "default"}
              disabled={isLoading}
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isLoading ? "Testing..." : "Test Connection"}
            </Button>
            {isConnected && (
              <div className="flex items-center gap-2 text-success">
                <CheckCircle2 className="h-4 w-4" />
                <span className="text-sm font-medium">Connected</span>
              </div>
            )}
          </div>

          {isConnected && (
            <div className="space-y-3 pt-4 border-t border-border">
              <Label>Select Tables (multiple)</Label>
              <div className="space-y-2 max-h-[300px] overflow-y-auto">
                {tables.map((table, index) => (
                  <div
                    key={table.name}
                    className={cn(
                      "flex items-center justify-between p-3 rounded-lg border transition-colors cursor-pointer",
                      table.checked ? "border-primary bg-primary/5" : "border-border bg-secondary",
                    )}
                    onClick={() => toggleTable(index)}
                  >
                    <div className="flex items-center gap-3">
                      <Checkbox checked={table.checked} onCheckedChange={() => toggleTable(index)} />
                      <div className="flex items-center gap-2">
                        <Database className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{table.name}</span>
                      </div>
                    </div>
                    <span className="text-sm text-muted-foreground">{table.rows.toLocaleString()} rows</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {isConnected && (
        <Button onClick={handleImport} className="w-full" size="lg">
          Import Data
        </Button>
      )}
    </div>
  )
}
