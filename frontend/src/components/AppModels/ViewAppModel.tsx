import { Link } from "@tanstack/react-router"
import { ExternalLink, Eye } from "lucide-react"
import { useState } from "react"

import type { AppModelPublic } from "~/client"
import { BpmnDiagram, RdfView } from "~/components/AppModels/ModelViews"
import { Button } from "~/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog"
import { DropdownMenuItem } from "~/components/ui/dropdown-menu"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs"

interface ViewAppModelProps {
  appmodel: AppModelPublic
}

const ViewAppModel = ({ appmodel }: ViewAppModelProps) => {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuItem
        onSelect={(e) => e.preventDefault()}
        onClick={() => setIsOpen(true)}
      >
        <Eye />
        View Model
      </DropdownMenuItem>
      <DialogContent className="flex h-[85vh] flex-col sm:max-w-[90vw]">
        <DialogHeader>
          <DialogTitle>{appmodel.title}</DialogTitle>
          <DialogDescription>
            The workflow stored in this model as a BPMN diagram, and the model's
            RDF source.
          </DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="bpmn" className="flex min-h-0 flex-1 flex-col">
          <div className="flex items-center justify-between">
            <TabsList>
              <TabsTrigger value="bpmn">BPMN Diagram</TabsTrigger>
              <TabsTrigger value="rdf">RDF</TabsTrigger>
            </TabsList>
            {/* the same view as a page with its own URL, for bookmarking/sharing */}
            <Button variant="ghost" size="sm" asChild>
              <Link to="/appmodels/$id" params={{ id: appmodel.id }}>
                <ExternalLink />
                Open page
              </Link>
            </Button>
          </div>
          <TabsContent value="bpmn" className="min-h-0 flex-1">
            <BpmnDiagram id={appmodel.id} title={appmodel.title} />
          </TabsContent>
          <TabsContent value="rdf" className="min-h-0 flex-1">
            <RdfView
              rdf={
                appmodel.knowledge_graph_rdf ?? "This model has no RDF content."
              }
            />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

export default ViewAppModel
