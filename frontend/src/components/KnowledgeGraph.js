import CytoscapeComponent from 'react-cytoscapejs';
import './KnowledgeGraph.css';
var KnowledgeGraph = function (_a) {
    var data = _a.data;
    var elements = data || [
        { data: { id: 'one', label: 'Node 1' }, position: { x: 0, y: 0 } },
        { data: { id: 'two', label: 'Node 2' }, position: { x: 100, y: 0 } },
        { data: { source: 'one', target: 'two', label: 'Edge 1-2' } }
    ];
    var stylesheet = [
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
    var layout = { name: 'cose', animate: true };
    return (<div className="knowledge-graph-container">
      <CytoscapeComponent elements={elements} style={{ width: '100%', height: '500px' }} stylesheet={stylesheet} layout={layout} cy={function (cy) {
            cy.on('mouseover', 'node', function (event) {
                var node = event.target;
                node.qtip({
                    content: node.data('label'),
                    position: { my: 'bottom center', at: 'top center' },
                    style: { classes: 'qtip-bootstrap' }
                });
            });
        }}/>
    </div>);
};
export default KnowledgeGraph;
