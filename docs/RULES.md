# Documentation Rules

## File Structure
```
/docs
  /components      # Individual component documentation
  /systems         # System-level documentation
  /scripts         # Script documentation
  /architecture    # Architecture diagrams and descriptions
  RULES.md         # Documentation rules
```

## Component Documentation Template
```markdown
# Component Name

## Purpose
Brief description of the component's purpose

## Dependencies
- List of dependencies
- Required modules
- External services

## Flow Diagram
```mermaid
// Component-specific flow diagram
```

## Methods
| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| method_name | param_type | return_type | Description |

## Error Handling
- List of possible errors
- How they are handled
- Recovery procedures

## Usage Examples
```python
# Example code
```

## Update Changelog
- Increment version number
- Add current date
- Update comparison links
- Maintain version history

## Update Relevant System Docs
- List out key system documentation files
- For example:
  - `/docs/systems/core-functionality.md`
  - `/docs/systems/data-processing.md` 
  - `/docs/systems/third-party-integrations.md`

## Update Requirements for New Code Elements
When adding new components, functions, classes, modules, or scripts:

1. **Component/Class Updates**
   - Add component/class documentation
   - Update cursor rules
   - Add language-specific comments (e.g., JSDoc, docstrings)
   - Update diagrams if needed

2. **Function/Method Updates**
   - Document parameters, return types, and exceptions
   - Update cursor rules
   - Add usage examples 
   - Update type definitions (if applicable)

3. **Module Updates** 
   - Create module documentation
   - Update cursor rules
   - Document dependencies and integration points
   - Update architecture diagrams

4. **Script Updates**
   - Document script purpose and usage
   - Update cursor rules
   - Add execution instructions 
   - Document environment and dependency requirements

5. **Type/Interface Updates**
   - List out key type/interface definition files
   - For example:
     - `/docs/types/common.md`
     - `/docs/types/api.md`

## Documentation Format

### Component/Class Documentation
\```language
/**
 * @component ComponentName
 * @description Brief description of purpose and usage
 * @prop {Type} propName - Description of each prop (if applicable)
 * @state {Type} stateName - Description of internal state (if applicable) 
 * @methods - List of public methods
 * @events - List of events handled/emitted (if applicable)
 * @example
 * // Example usage of component/class 
 * @updates
 * 1. Update component/class documentation
 * 2. Update cursor rules
 * 3. Add language-specific comments  
 * 4. Update diagrams if needed
 * 5. Update type definitions (if applicable)
 */
\```

### Function/Method Documentation
\```language
/**
 * @function functionName
 * @description What the function/method does 
 * @param {Type} paramName - Parameter description
 * @returns {Type} Description of return value
 * @throws {ErrorType} Description of error thrown (if applicable)
 * @example 
 * // Example usage of function/method
 * @updates
 * 1. Update function/method documentation
 * 2. Update cursor rules
 * 3. Add usage examples
 * 4. Update type definitions (if applicable) 
 */
\``` 

### Module Documentation 
\```language
/**
 * @module ModuleName 
 * @description Module purpose and scope
 * @exports {Type} exportName - Description
 * @requires {ModuleName} - Description of required module  
 * @example
 * // Example usage of module
 * @updates 
 * 1. Create module documentation
 * 2. Update cursor rules
 * 3. Document dependencies and integration points
 * 4. Update architecture diagrams
 */
\```

### Script Documentation
\```language
/**
 * @script scriptName
 * @description Purpose and functionality 
 * @env - Required environment variables
 * @dependencies - Required dependencies 
 * @input - Expected input format/files
 * @output - Expected output/side effects
 * @example
 * # Example usage of script 
 * @updates
 * 1. Update script documentation 
 * 2. Update execution commands
 * 3. Update environment and dependency requirements 
 * 4. Update flow diagrams
 */
\```

### Architecture Documentation 
\```markdown
# Component/System Name
## Overview
Brief description of purpose and role 
## Flow Diagram
Include language-agnostic diagram of component/system 
## Integration Points
- List external services
- List internal dependencies 
- Describe data flows
## Configuration
Explain required setup and configuration 
## Error Handling 
Describe error scenarios and handling
\```

## File Organization

### Documentation Location
- Component/Class docs: `/docs/components/[component-name].md`
- System docs: `/docs/systems/[system-name].md` 
- Architecture docs: `/docs/architecture/[topic].md`
- Script docs: `/docs/scripts/[script-name].md`

### Template Structure 
Each documentation file should include:
1. Title and brief description
2. System/component diagram if applicable
3. Code examples in relevant language 
4. Integration points
5. Configuration requirements
6. Error handling 
7. Update requirements

## Best Practices
1. Keep diagrams language-agnostic and up to date
2. Include language-specific type definitions 
3. Document error scenarios
4. Cross-reference related documentation 
5. Include practical usage examples
6. Document environment and dependency requirements 
7. Maintain consistent formatting
8. Update relevant architecture diagrams

## Validation
- Run documentation linting
- Verify all links work 
- Ensure diagrams are current
- Check type definitions match
- Validate environment variables 

## Version Tracking
- Document notable changes in CHANGELOG
- Include version in documentation headers 
- Tag documentation updates with git tags

## Markdown Standards
- Use triple backticks for code blocks with language identifier
- Use headers consistently (H1 for title, H2 for sections) 
- Use lists for related items
- Use tables for structured data
- Use blockquotes for important notes 

## Diagram Standards 
- Use Mermaid for diagrams but escape special characters as to not break cursor ide rendering
- Show relationships between components/systems
- Include diagram source in markdown
- Use consistent styling across diagrams