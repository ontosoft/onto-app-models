import { rankWith, uiTypeIs, optionIs, RankedTester, and } from "@jsonforms/core"; 

// // Define a custom tester for the "Actions" type
// export default rankWith(
//   3, // Priority rank (higher means more likely to match)
//   uiTypeIs("button") // Match UI schema elements with type "Actions"
// );
// const isFunctionButton: Tester = (uischema, _schema, _rootSchema) => {
//   return rankWith(3, uischema.type === 'button' && optionIs('buttonType', 'danger'));
// };

const isSubmitButton: RankedTester = rankWith(
  3,
//  and(
    uiTypeIs('button'),
    //optionIs('onClick', 'submit'),
 // )
);


export {  isSubmitButton };