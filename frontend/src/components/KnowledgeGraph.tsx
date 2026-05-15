import CytoscapeComponent from 'react-cytoscapejs';
import './KnowledgeGraph.css';

const KnowledgeGraph = ({ data }: { data: any }) => {
  const elements = data || [
    { data: { id: 'one', label: 'Node 1' }, position: { x: 0, y: 0 } },
    { data: { id: 'two', label: 'Node 2' }, position: { x: 100, y: 0 } },
    { data: { source: 'one', target: 'two', label: 'Edge 1-2' } }
  ];

  const stylesheet = [
    {
      selector: 'node',
      style: {
        'background-color': '#0074D9',
        'label': 'data(label)',
        'text-valign': 'center',
        'color': '#fff',
        'text-outline-width': 2,
        'text-outline-color': '#0074D9'
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 3,
        'line-color': '#ccc',
        'target-arrow-color': '#ccc',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier'
      }
    }
  ];

  const layout = { name: 'cose', animate: true };

  return (
    <div className="knowledge-graph-container">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '500px' }}
        stylesheet={stylesheet}
        layout={layout}
        cy={(cy: any) => {
          cy.on('mouseover', 'node', (event: any) => {
            const node = event.target;
            node.qtip({
              content: node.data('label'),
              position: { my: 'bottom center', at: 'top center' },
              style: { classes: 'qtip-bootstrap' }
            });
          });
        }}
      />
    </div>
  );
};

export default KnowledgeGraph;
