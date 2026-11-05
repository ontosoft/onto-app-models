import { defineConfig } from "@hey-api/openapi-ts"

// Mirrors the upstream full-stack-fastapi-template migration to
// @hey-api/openapi-ts 0.97.x: axios client with thrown errors (AxiosError),
// static service classes named like the legacy client (AppmodelsService...),
// method names derived from the "{tag}-{route_name}" operation ids.
export default defineConfig({
  input: "./openapi.json",
  output: "./src/client",

  plugins: [
    { name: "@hey-api/client-axios", throwOnError: true },
    { name: "@hey-api/typescript", case: "preserve" },
    {
      name: "@hey-api/sdk",
      operations: {
        // NOTE: this doesn't allow tree-shaking
        strategy: "byTags",
        methods: "static",
        containerName: "{{name}}Service",
        methodName: (name: string): string => name.replace(/^[^-]*-/, ""),
      },
    },
    {
      name: "@hey-api/schemas",
      type: "json",
    },
  ],
})
