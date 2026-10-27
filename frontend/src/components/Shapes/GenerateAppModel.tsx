import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Wand2 } from "lucide-react"

import { ShapesService } from "~/client"
import { Button } from "~/components/ui/button"
import useCustomToast from "~/hooks/useCustomToast"
import { handleError } from "~/utils"

interface GenerateAppModelProps {
  id: string
}

/**
 * Generates a FAM candidate from a shapes document with the rule-based
 * converter. The result appears under App-models (origin "rule-based").
 */
const GenerateAppModel = ({ id }: GenerateAppModelProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () => ShapesService.generateAppmodelFromShapesDocument({ id }),
    onSuccess: (model) => {
      showSuccessToast(`Model "${model.title}" generated - see App-models`)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["appmodels"] })
      queryClient.invalidateQueries({ queryKey: ["shapes"] })
    },
  })

  return (
    <Button
      variant="outline"
      size="sm"
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      <Wand2 className="mr-1 size-4" />
      {mutation.isPending ? "Generating..." : "Generate"}
    </Button>
  )
}

export default GenerateAppModel
