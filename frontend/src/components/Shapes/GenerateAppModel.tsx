import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Wand2 } from "lucide-react"

import { ShapesService } from "~/client"
import { Button } from "~/components/ui/button"
import useCustomToast from "~/hooks/useCustomToast"
import { handleError } from "~/utils"

interface GenerateAppModelProps {
  id: string
  onSuccess?: () => void
}

/**
 * Generates a FAM candidate from a shapes document with the rule-based
 * converter. The candidate shows up in the row's expanded sub-list (and
 * under App-models, origin "rule-based").
 */
const GenerateAppModel = ({ id, onSuccess }: GenerateAppModelProps) => {
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () => ShapesService.generateAppmodelFromShapesDocument({ id }),
    onSuccess: (model) => {
      showSuccessToast(`Model "${model.title}" generated`)
      onSuccess?.()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["appmodels"] })
      // Prefix match also invalidates ["shapes", id, "appmodels"].
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
